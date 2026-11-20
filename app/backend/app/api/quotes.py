"""Quotations with item-level customer approvals (evidence required, no implicit approvals)."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.api.jobs import get_job, require_open
from app.core.audit import audit
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (Approval, PartPurchase, Quotation, QuotationItem, RepairOperation, VehicleVisit)
from app.models.auth import User
from app.services.work_approval import lock_job
from app.services.pricing import effective_qty, line_price
from app.services.job_status import QUOTATION_STAGES, sync_work_status, transition_status

router = APIRouter(prefix="/api", tags=["quotes"])
METHODS = ("in_person", "phone", "whatsapp", "signed", "other")
PRE_APPROVAL_STATUSES = ("received", "inspection_pending", "under_inspection", "waiting_quotation")


class QuoteCreate(BaseModel):
    from_job: bool = True  # pre-fill items from the job's operations and parts
    valid_until: date | None = None
    terms: str | None = None
    discount: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    tax_rate: Decimal = Field(Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)  # never assumed


class QuotePatch(BaseModel):
    valid_until: date | None = None
    terms: str | None = None
    discount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)


class ItemIn(BaseModel):
    kind: str = Field(pattern="^(labor|part|other)$")
    description: str = Field(min_length=2)
    quantity: Decimal = Field(Decimal("1"), gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class Decision(BaseModel):
    item_id: int
    decision: str = Field(pattern="^(approved|rejected)$")


class ApprovalIn(BaseModel):
    decisions: list[Decision] | None = None  # omitted => the whole quotation
    decision: str | None = Field(None, pattern="^(approved|rejected)$")  # used with whole-quote approvals
    method: str
    evidence: str = Field(min_length=3)


def _effective_status(q: Quotation) -> str:
    if q.status == "sent" and q.valid_until and q.valid_until < date.today():
        return "expired"
    return q.status


def recalc(db: DbSession, q: Quotation) -> None:
    db.flush()
    items = list(db.scalars(select(QuotationItem).where(QuotationItem.quotation_id == q.id)))
    q.subtotal = sum((Decimal(i.amount) for i in items), Decimal("0.00"))
    if Decimal(q.discount) > q.subtotal:
        raise AppError("الخصم أكبر من إجمالي العرض", 422, "bad_discount")
    q.tax_amount = to_money((q.subtotal - Decimal(q.discount)) * Decimal(q.tax_rate) / 100)
    q.grand_total = q.subtotal - Decimal(q.discount) + q.tax_amount


def quote_out(db: DbSession, q: Quotation) -> dict:
    items = list(db.scalars(select(QuotationItem).where(QuotationItem.quotation_id == q.id).order_by(QuotationItem.id)))
    approved_sub = sum((Decimal(i.amount) for i in items if i.approval_state == "approved"), Decimal("0.00"))
    factor = (Decimal(q.grand_total) / Decimal(q.subtotal)) if Decimal(q.subtotal) else Decimal(0)
    approvals = db.scalars(select(Approval).where(Approval.quotation_id == q.id).order_by(Approval.id))
    return {"id": str(q.id), "quote_no": q.quote_no, "visit_id": str(q.visit_id), "status": _effective_status(q),
            "valid_until": q.valid_until, "terms": q.terms, "discount": str(q.discount), "tax_rate": str(q.tax_rate),
            "subtotal": str(q.subtotal), "tax_amount": str(q.tax_amount), "grand_total": str(q.grand_total),
            "approved_amount": str(to_money(approved_sub * factor)), "sent_at": q.sent_at,
            "items": [{"id": i.id, "kind": i.kind, "description": i.description, "quantity": str(i.quantity),
                       "unit_price": str(i.unit_price), "amount": str(i.amount), "approval_state": i.approval_state,
                       "operation_id": i.operation_id, "part_id": i.part_id} for i in items],
            "approvals": [{"id": a.id, "item_ids": a.item_ids, "decision": a.decision, "method": a.method,
                           "evidence": a.evidence, "decided_at": a.decided_at} for a in approvals]}


def _get_quote(db: DbSession, qid: UUID, *, lock: bool = False) -> Quotation:
    q = (db.scalar(select(Quotation).where(Quotation.id == qid).with_for_update().execution_options(populate_existing=True))
         if lock else db.get(Quotation, qid))
    if not q:
        raise AppError("عرض السعر غير موجود", 404, "not_found")
    return q


def _require_draft(q: Quotation) -> None:
    if q.status != "draft":
        raise AppError("عرض السعر أُرسل بالفعل، أنشئ نسخة جديدة للتعديل", 409, "not_draft")


@router.post("/jobs/{job_id}/quotations", status_code=201)
def create_quote(job_id: UUID, body: QuoteCreate, request: Request, user: User = Depends(require("quotes.write")),
                 db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    require_open(job)
    q = Quotation(visit_id=job.id, customer_id=job.customer_id, vehicle_id=job.vehicle_id, created_by=user.id,
                  valid_until=body.valid_until, terms=body.terms, discount=body.discount, tax_rate=body.tax_rate)
    db.add(q)
    db.flush()
    if body.from_job:
        for op in db.scalars(select(RepairOperation).where(RepairOperation.visit_id == job.id,
                                                           RepairOperation.status != "cancelled").order_by(RepairOperation.id)):
            db.add(QuotationItem(quotation_id=q.id, operation_id=op.id, kind="labor", description=op.description,
                                 quantity=Decimal("1"), unit_price=op.labor_amount, amount=op.labor_amount))
        for p in db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job.id).order_by(PartPurchase.id)):
            qty = effective_qty(db, p)
            if qty > 0:
                db.add(QuotationItem(quotation_id=q.id, part_id=p.id, operation_id=p.operation_id, kind="part",
                                     description=p.part_name, quantity=qty, unit_price=p.unit_price,
                                     amount=line_price(db, p)))
    recalc(db, q)
    audit(db, user, "quote.create", "quotation", q.id, after={"quote_no": q.quote_no, "total": str(q.grand_total)},
          ip=client_ip(request))
    if job.status in QUOTATION_STAGES:
        transition_status(db, job, "waiting_quotation", user, "تلقائي: جارٍ إعداد عرض السعر", client_ip(request))
    return quote_out(db, q)


@router.get("/jobs/{job_id}/quotations")
def job_quotes(job_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    get_job(db, job_id)
    return [quote_out(db, q) for q in db.scalars(select(Quotation).where(Quotation.visit_id == job_id).order_by(Quotation.quote_no))]


@router.get("/quotations/{qid}")
def get_quote(qid: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    q = _get_quote(db, qid)
    d = quote_out(db, q)
    job = db.get(VehicleVisit, q.visit_id)
    d["job_no"] = job.visit_no
    return d


@router.patch("/quotations/{qid}")
def patch_quote(qid: UUID, body: QuotePatch, request: Request, user: User = Depends(require("quotes.write")),
                db: DbSession = Depends(get_db, scope="function")):
    q = _get_quote(db, qid)
    _require_draft(q)
    before = {"discount": str(q.discount), "tax_rate": str(q.tax_rate), "valid_until": q.valid_until}
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(q, k, v)
    recalc(db, q)
    audit(db, user, "quote.update", "quotation", q.id, before=before,
          after={"discount": str(q.discount), "tax_rate": str(q.tax_rate), "valid_until": q.valid_until},
          ip=client_ip(request))
    return quote_out(db, q)


@router.post("/quotations/{qid}/items", status_code=201)
def add_item(qid: UUID, body: ItemIn, request: Request, user: User = Depends(require("quotes.write")),
             db: DbSession = Depends(get_db, scope="function")):
    q = _get_quote(db, qid)
    _require_draft(q)
    db.add(QuotationItem(quotation_id=q.id, kind=body.kind, description=body.description, quantity=body.quantity,
                         unit_price=body.unit_price, amount=to_money(body.quantity * body.unit_price)))
    recalc(db, q)
    audit(db, user, "quote.item_add", "quotation", q.id, after={"description": body.description}, ip=client_ip(request))
    return quote_out(db, q)


@router.delete("/quotations/{qid}/items/{item_id}")
def remove_item(qid: UUID, item_id: int, request: Request, user: User = Depends(require("quotes.write")),
                db: DbSession = Depends(get_db, scope="function")):
    q = _get_quote(db, qid)
    _require_draft(q)
    item = db.get(QuotationItem, item_id)
    if not item or item.quotation_id != q.id:
        raise AppError("البند غير موجود", 404, "not_found")
    db.delete(item)
    recalc(db, q)
    audit(db, user, "quote.item_remove", "quotation", q.id, before={"description": item.description}, ip=client_ip(request))
    return quote_out(db, q)


@router.post("/quotations/{qid}/send")
def send_quote(qid: UUID, request: Request, user: User = Depends(require("quotes.write")),
               db: DbSession = Depends(get_db, scope="function")):
    q = _get_quote(db, qid, lock=True)
    lock_job(db, q.visit_id)
    _require_draft(q)
    if not Decimal(q.subtotal):
        raise AppError("أضف بنود لعرض السعر قبل الإرسال", 422, "empty_quote")
    q.status, q.sent_at = "sent", datetime.now(timezone.utc)
    job = db.get(VehicleVisit, q.visit_id)
    if job.status in (*PRE_APPROVAL_STATUSES, "waiting_parts"):
        transition_status(db, job, "waiting_approval", user, f"أُرسل عرض السعر #{q.quote_no}", client_ip(request))
    audit(db, user, "quote.send", "quotation", q.id, ip=client_ip(request))
    return quote_out(db, q)


@router.post("/quotations/{qid}/approvals")
def record_approval(qid: UUID, body: ApprovalIn, request: Request, user: User = Depends(require("quotes.approve")),
                    db: DbSession = Depends(get_db, scope="function")):
    q = _get_quote(db, qid, lock=True)
    lock_job(db, q.visit_id)
    status = _effective_status(q)
    if status == "expired":
        raise AppError("انتهت صلاحية عرض السعر", 409, "expired")
    if status not in ("sent", "partially_approved"):
        raise AppError("لا يمكن تسجيل موافقة إلا على عرض مُرسل", 409, "not_sent")
    if body.method not in METHODS:
        raise AppError("طريقة الموافقة غير معروفة", 422, "bad_method")
    items = {i.id: i for i in db.scalars(select(QuotationItem).where(QuotationItem.quotation_id == q.id))}
    if body.decisions:
        decisions = {d.item_id: d.decision for d in body.decisions}
    elif body.decision:
        decisions = {iid: body.decision for iid, i in items.items() if i.approval_state == "pending"}
    else:
        raise AppError("حدد القرار", 422, "no_decision")
    if not decisions:
        raise AppError("لا توجد بنود معلقة", 409, "nothing_pending")
    for iid in decisions:
        if iid not in items:
            raise AppError("بند غير موجود في عرض السعر", 422, "bad_item")
        if items[iid].approval_state != "pending":
            raise AppError("تم اتخاذ قرار على هذا البند من قبل", 409, "already_decided")
    for decision in ("approved", "rejected"):
        ids = [iid for iid, d in decisions.items() if d == decision]
        if ids:
            for iid in ids:
                items[iid].approval_state = decision
            db.add(Approval(quotation_id=q.id, item_ids=",".join(map(str, ids)), decision=decision,
                            method=body.method, evidence=body.evidence.strip(), recorded_by=user.id))
    states = [i.approval_state for i in items.values()]
    if "pending" in states:
        q.status = "partially_approved" if "approved" in states else q.status
    elif all(s == "approved" for s in states):
        q.status = "approved"
    elif all(s == "rejected" for s in states):
        q.status = "rejected"
    else:
        q.status = "partially_approved"
    job = db.get(VehicleVisit, q.visit_id)
    if q.status in ("approved", "partially_approved") and job.status == "waiting_approval":
        transition_status(db, job, "in_progress", user, f"موافقة العميل على عرض السعر #{q.quote_no}", client_ip(request))
        sync_work_status(db, job, user, "تلقائي: تحديث تقدم العمل بعد موافقة العميل", client_ip(request))
    stock_warnings = _sync_warehouse_stock(db, items, decisions, user)
    audit(db, user, "quote.approval", "quotation", q.id, after={"decisions": {str(k): v for k, v in decisions.items()},
                                                               "method": body.method, "evidence": body.evidence},
          ip=client_ip(request))
    db.flush()
    out = quote_out(db, q)
    if stock_warnings:
        out["stock_warnings"] = stock_warnings  # approval is recorded; these parts could not be reserved (not enough stock)
    return out


def _sync_warehouse_stock(db: DbSession, items: dict, decisions: dict, user: User) -> list[dict]:
    """Customer approval reserves warehouse stock for the approved parts; a rejection gives it back. A shortage never blocks recording the
    customer's decision: it is reported so the workshop can order stock."""
    from app.services import inventory as inv_svc
    warnings: list[dict] = []
    for iid, decision in decisions.items():
        item = items[iid]
        part = db.get(PartPurchase, item.part_id) if item.part_id else None
        if part is None or part.source != "warehouse" or part.status in ("cancelled", "returned"):
            continue
        if decision == "rejected":
            inv_svc.release(db, part, user, "quotation item rejected by the customer")
            continue
        try:
            with db.begin_nested():  # a failed reservation must not undo the approval itself
                inv_svc.sync_reservation(db, part, user, "customer approved the quotation")
        except AppError as e:
            warnings.append({"part_id": part.id, "part_name": part.part_name, "code": e.code, "message": e.message})
    return warnings
