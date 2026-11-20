"""Invoices, payments (partial/deposits), refunds, credit notes. Money is Decimal end to end."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.api.jobs import get_job, require_open
from app.api.settings_api import format_number
from app.services import settings as cfg
from app.core.audit import audit
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (CreditNote, Customer, Invoice, InvoiceItem, PartPurchase, Payment, Quotation,
                        QuotationItem, Refund, RepairOperation, Vehicle, VehicleVisit)
from app.models.auth import AuditLog, User
from app.services import invoice_doc, invoice_pdf
from app.services.pricing import compute_totals, effective_qty, returned_map

router = APIRouter(prefix="/api", tags=["billing"])

ZERO = Decimal("0.00")


# ---- helpers ------------------------------------------------------------------
def unbilled_work(db: DbSession, job_id: UUID) -> tuple[list[RepairOperation], list[tuple[PartPurchase, Decimal]]]:
    """Find work not covered by issued invoices, including any remaining part quantity."""
    lines = db.execute(select(InvoiceItem.operation_id, InvoiceItem.part_id, InvoiceItem.quantity)
                       .join(Invoice).where(Invoice.visit_id == job_id, Invoice.status == "issued"))
    billed_operations = set()
    billed_parts: dict[int, Decimal] = {}
    for operation_id, part_id, quantity in lines:
        if operation_id is not None:
            billed_operations.add(operation_id)
        if part_id is not None:
            billed_parts[part_id] = billed_parts.get(part_id, ZERO) + quantity
    operations = [op for op in db.scalars(select(RepairOperation).where(
        RepairOperation.visit_id == job_id, RepairOperation.status != "cancelled").order_by(RepairOperation.id))
                  if op.id not in billed_operations]
    parts = []
    returned = returned_map(db, job_id)
    for part in db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job_id).order_by(PartPurchase.id)):
        if part.source == "warehouse" and Decimal(part.issued_qty) <= 0:
            continue  # stock that has not left the warehouse is not billable yet (its cost is only known at issue)
        quantity = effective_qty(db, part, returned) - billed_parts.get(part.id, ZERO)
        if quantity > 0:
            parts.append((part, quantity))
    return operations, parts


def _get_invoice(db: DbSession, invoice_id: UUID, lock: bool = False) -> Invoice:
    q = select(Invoice).where(Invoice.id == invoice_id)
    if lock:
        q = q.with_for_update().execution_options(populate_existing=True)  # serialises concurrent payments/credits on the same invoice
    inv = db.scalar(q)
    if not inv:
        raise AppError("الفاتورة غير موجودة", 404, "not_found")
    return inv


def _sum(db: DbSession, col, *where) -> Decimal:
    return to_money(db.scalar(select(func.coalesce(func.sum(col), 0)).where(*where)))


def money_state(db: DbSession, inv: Invoice, *, at_delivery: datetime | None = None) -> dict:
    payments = [Payment.invoice_id == inv.id]
    refunds = [Refund.payment_id.in_(select(Payment.id).where(Payment.invoice_id == inv.id))]
    credits = [CreditNote.invoice_id == inv.id]
    if at_delivery is not None:
        payments.append(Payment.paid_at <= at_delivery)
        refunds.append(Refund.refunded_at <= at_delivery)
        credits.append(CreditNote.created_at <= at_delivery)
    return _state(inv, _sum(db, Payment.amount, *payments), _sum(db, Refund.amount, *refunds),
                  _sum(db, CreditNote.amount, *credits), status="issued" if at_delivery is not None else inv.status)


def money_states(db: DbSession, invoices: list[Invoice]) -> dict:
    """Same result as money_state for many invoices using three grouped queries (reports over thousands of invoices)."""
    ZERO = Decimal("0.00")
    ids = [i.id for i in invoices]
    if not ids:
        return {}
    paid = {k: to_money(v) for k, v in db.execute(select(Payment.invoice_id, func.sum(Payment.amount)).where(Payment.invoice_id.in_(ids)).group_by(Payment.invoice_id))}
    refunded = {k: to_money(v) for k, v in db.execute(select(Payment.invoice_id, func.sum(Refund.amount)).join(Refund, Refund.payment_id == Payment.id).where(Payment.invoice_id.in_(ids)).group_by(Payment.invoice_id))}
    credits = {k: to_money(v) for k, v in db.execute(select(CreditNote.invoice_id, func.sum(CreditNote.amount)).where(CreditNote.invoice_id.in_(ids)).group_by(CreditNote.invoice_id))}
    return {i.id: _state(i, paid.get(i.id, ZERO), refunded.get(i.id, ZERO), credits.get(i.id, ZERO)) for i in invoices}


def _state(inv: Invoice, paid: Decimal, refunded: Decimal, credits: Decimal, *, status: str | None = None) -> dict:
    net_paid = paid - refunded
    due = Decimal(inv.total) - credits
    outstanding = due - net_paid
    invoice_status = status or inv.status
    if invoice_status == "draft":
        status = "draft"
    elif invoice_status == "cancelled":
        status = "void"
    elif outstanding < 0:
        status = "overpaid"
    elif outstanding == 0:
        status = "paid"
    elif net_paid > 0:
        status = "partial"
    else:
        status = "unpaid"
    return {"paid": paid, "refunded": refunded, "credit_total": credits, "net_paid": net_paid, "due": due,
            "outstanding": outstanding, "payment_status": status}


def _recalc(db: DbSession, inv: Invoice) -> None:
    db.flush()
    inv.subtotal = _sum(db, InvoiceItem.amount, InvoiceItem.invoice_id == inv.id)
    if Decimal(inv.discount) > inv.subtotal:
        raise AppError("الخصم أكبر من إجمالي الفاتورة", 422, "bad_discount")
    inv.tax_amount, inv.total = compute_totals(inv.subtotal, inv.discount, inv.tax_rate)


def invoice_out(db: DbSession, inv: Invoice) -> dict:
    return invoice_outs(db, [inv])[0]


def _group(rows, key) -> dict:
    out: dict = {}
    for r in rows:
        out.setdefault(key(r), []).append(r)
    return out


def invoice_outs(db: DbSession, invoices: list[Invoice]) -> list[dict]:
    """Serialise many invoices with a fixed number of queries (not ~10 per invoice)."""
    if not invoices:
        return []
    ids = [i.id for i in invoices]
    states = money_states(db, invoices)
    items_by = _group(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id.in_(ids)).order_by(InvoiceItem.id)), lambda r: r.invoice_id)
    all_pays = list(db.scalars(select(Payment).where(Payment.invoice_id.in_(ids)).order_by(Payment.id)))
    pays_by = _group(all_pays, lambda r: r.invoice_id)
    refs_by = _group(db.scalars(select(Refund).where(Refund.payment_id.in_([p.id for p in all_pays])).order_by(Refund.id)), lambda r: r.payment_id) if all_pays else {}
    all_credits = list(db.scalars(select(CreditNote).where(CreditNote.invoice_id.in_(ids)).order_by(CreditNote.id)))
    credits_by = _group(all_credits, lambda r: r.invoice_id)
    cancelled_credits = set(db.scalars(select(AuditLog.entity_id).where(
        AuditLog.action == "credit_note.cancel", AuditLog.entity_type == "credit_note",
        AuditLog.entity_id.in_([str(c.id) for c in all_credits])))) if all_credits else set()
    jobs = {j.id: j for j in db.scalars(select(VehicleVisit).where(VehicleVisit.id.in_({i.visit_id for i in invoices})))}
    custs = {c.id: c for c in db.scalars(select(Customer).where(Customer.id.in_({i.customer_id for i in invoices})))}
    vehs = {v.id: v for v in db.scalars(select(Vehicle).where(Vehicle.id.in_({i.vehicle_id for i in invoices})))}
    return [_invoice_dict(db, inv, states[inv.id], items_by.get(inv.id, []), pays_by.get(inv.id, []), refs_by,
                          credits_by.get(inv.id, []), cancelled_credits, jobs[inv.visit_id], custs[inv.customer_id], vehs[inv.vehicle_id])
            for inv in invoices]


def _invoice_dict(db, inv, st, items, payments, refs_by, credits, cancelled_credits, job, cust, veh) -> dict:
    pays = []
    for p in payments:
        refs = refs_by.get(p.id, [])
        pays.append({"id": p.id, "kind": p.kind, "amount": f"{Decimal(p.amount):.2f}", "method": p.method, "reference": p.reference,
                     "paid_at": p.paid_at, "refunded": str(sum((Decimal(r.amount) for r in refs), ZERO)),
                     "refunds": [{"id": r.id, "amount": f"{Decimal(r.amount):.2f}", "reason": r.reason, "refunded_at": r.refunded_at} for r in refs]})
    return {"id": str(inv.id), "invoice_no": inv.invoice_no, "number": format_number(db, "invoice", inv.invoice_no), "status": inv.status,
            "visit_id": str(inv.visit_id), "job_no": job.visit_no, "currency": inv.currency,
            "customer": {"id": str(cust.id), "name": cust.full_name, "mobile": cust.mobile},
            "vehicle": {"id": str(veh.id), "make": veh.make, "model": veh.model, "plate": veh.plate},
            "invoice_date": inv.invoice_date, "due_date": inv.due_date, "notes": inv.notes,
            "discount": f"{Decimal(inv.discount):.2f}", "tax_rate": f"{Decimal(inv.tax_rate):.2f}", "subtotal": str(inv.subtotal),
            "tax_amount": str(inv.tax_amount), "total": str(inv.total), "issued_at": inv.issued_at,
            "cancel_reason": inv.cancel_reason, **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in st.items()},
            "items": [{"id": i.id, "kind": i.kind, "description": i.description, "quantity": str(i.quantity),
                       "unit_price": str(i.unit_price), "amount": str(i.amount)} for i in items],
            "payments": pays,
            "credit_notes": [{"id": c.id, "number": format_number(db, "credit", c.credit_no), "amount": f"{Decimal(c.amount):.2f}", "reason": c.reason,
                              "created_at": c.created_at, "cancelled": str(c.id) in cancelled_credits, "is_reversal": c.amount < 0} for c in credits]}


def _idempotent(db: DbSession, model, key: str | None):
    return db.scalar(select(model).where(model.idempotency_key == key)) if key else None


# ---- invoices -----------------------------------------------------------------
class InvoiceCreate(BaseModel):
    supplemental: bool = False
    scope: str = Field("all", pattern="^(all|labor|parts)$")
    quotation_id: UUID | None = None  # bill only the customer-approved items of this quotation
    discount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    due_date: date | None = None
    notes: str | None = None


class InvoicePatch(BaseModel):
    discount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    due_date: date | None = None
    notes: str | None = None


class ItemIn(BaseModel):
    kind: str = Field(pattern="^(labor|part|other)$")
    description: str = Field(min_length=2)
    quantity: Decimal = Field(Decimal("1"), gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3)


@router.post("/jobs/{job_id}/invoices", status_code=201)
def create_invoice(job_id: UUID, body: InvoiceCreate, request: Request,
                   idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=100),
                   user: User = Depends(require("billing.write")), db: DbSession = Depends(get_db, scope="function")):
    prior = _idempotent(db, Invoice, idempotency_key)
    if prior:  # same click replayed, scoped to the original job
        if prior.visit_id != job_id:
            raise AppError("مفتاح التكرار مستخدم لعملية مختلفة", 409, "key_reused")
        return invoice_out(db, prior)
    job = get_job(db, job_id, lock=True)
    if job.status == "cancelled":
        raise AppError("أمر الصيانة ملغي", 409, "job_cancelled")
    prior = _idempotent(db, Invoice, idempotency_key)  # re-check now that we hold the lock
    if prior:
        if prior.visit_id != job_id:
            raise AppError("مفتاح التكرار مستخدم لعملية مختلفة", 409, "key_reused")
        return invoice_out(db, prior)
    existing = list(db.scalars(select(Invoice).where(Invoice.visit_id == job.id, Invoice.status != "cancelled")))
    if existing and (not body.supplemental or any(i.status == "draft" for i in existing)):
        raise AppError("يوجد فاتورة سارية لهذا الأمر بالفعل", 409, "duplicate_invoice")
    if body.supplemental and job.status == "delivered":
        raise AppError("أعد فتح أمر الشغل قبل إضافة فاتورة جديدة", 409, "job_closed")
    if body.supplemental and body.quotation_id:
        raise AppError("الفاتورة الإضافية تُنشأ من الأعمال غير المفوترة فقط", 422, "supplemental_quotation")
    quote = None
    if body.quotation_id:
        quote = db.get(Quotation, body.quotation_id)
        if not quote or quote.visit_id != job.id:
            raise AppError("عرض السعر لا يخص هذا الأمر", 422, "bad_quotation")
    inv = Invoice(visit_id=job.id, customer_id=job.customer_id, vehicle_id=job.vehicle_id, created_by=user.id,
                  quotation_id=quote.id if quote else None, due_date=body.due_date, notes=body.notes,
                  discount=body.discount or ZERO,
                  tax_rate=body.tax_rate if body.tax_rate is not None else (quote.tax_rate if quote else Decimal(cfg.get_section(db, "finance")["default_tax_rate"])),
                  currency=cfg.get_section(db, "finance")["currency"],
                  idempotency_key=idempotency_key)
    db.add(inv)
    db.flush()
    if quote:
        approved = db.scalars(select(QuotationItem).where(QuotationItem.quotation_id == quote.id,
                                                          QuotationItem.approval_state == "approved").order_by(QuotationItem.id))
        for i in approved:
            if body.scope != "all" and i.kind != ("part" if body.scope == "parts" else "labor"):
                continue
            if i.part_id:
                listed = db.get(PartPurchase, i.part_id)
                if listed is not None and listed.source == "warehouse" and Decimal(listed.issued_qty) <= 0:
                    continue  # warehouse part not issued yet: billed later, when its cost is known
            db.add(InvoiceItem(invoice_id=inv.id, kind=i.kind, description=i.description, quantity=i.quantity,
                               unit_price=i.unit_price, amount=i.amount, operation_id=i.operation_id, part_id=i.part_id))
    else:
        operations, parts = unbilled_work(db, job.id)
        if body.scope != "parts":
            for op in operations:
                db.add(InvoiceItem(invoice_id=inv.id, kind="labor", description=op.description, quantity=Decimal("1"),
                                   unit_price=op.labor_amount, amount=op.labor_amount, operation_id=op.id))
        if body.scope != "labor":
            for part, quantity in parts:
                db.add(InvoiceItem(invoice_id=inv.id, kind="part", description=part.part_name, quantity=quantity,
                                   unit_price=part.unit_price, amount=to_money(quantity * part.unit_price), part_id=part.id))
    db.flush()
    if (body.supplemental or body.scope != "all") and not db.scalar(select(InvoiceItem.id).where(InvoiceItem.invoice_id == inv.id)):
        raise AppError("لا توجد أعمال أو قطع جديدة غير مفوترة", 409, "nothing_to_invoice")
    if quote and body.discount is None and Decimal(quote.discount) > 0 and Decimal(quote.subtotal) > 0:
        # the customer agreed to the quoted (discounted) price: carry the quote's discount, pro rata to what is billed now
        inv.discount = to_money(Decimal(quote.discount) * _sum(db, InvoiceItem.amount, InvoiceItem.invoice_id == inv.id) / Decimal(quote.subtotal))
    _recalc(db, inv)
    audit(db, user, "invoice.create", "invoice", inv.id, after={"job": job.visit_no, "total": str(inv.total), "scope": body.scope, "supplemental": body.supplemental},
          ip=client_ip(request))
    return invoice_out(db, inv)


@router.get("/invoices")
def list_invoices(status: str | None = None, payment_status: str | None = None, customer_id: UUID | None = None,
                  limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), _: User = Depends(require("billing.read")),
                  db: DbSession = Depends(get_db, scope="function")):
    q = select(Invoice).order_by(Invoice.invoice_no.desc())
    if status:
        q = q.where(Invoice.status == status)
    if customer_id:
        q = q.where(Invoice.customer_id == customer_id)
    if payment_status:
        paid = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.invoice_id == Invoice.id).correlate(Invoice).scalar_subquery()
        refunded = select(func.coalesce(func.sum(Refund.amount), 0)).join(
            Payment, Payment.id == Refund.payment_id).where(
            Payment.invoice_id == Invoice.id).correlate(Invoice).scalar_subquery()
        credits = select(func.coalesce(func.sum(CreditNote.amount), 0)).where(
            CreditNote.invoice_id == Invoice.id).correlate(Invoice).scalar_subquery()
        net_paid = paid - refunded
        outstanding = Invoice.total - credits - net_paid
        state = case(
            (Invoice.status == "draft", "draft"),
            (Invoice.status == "cancelled", "void"),
            (outstanding < 0, "overpaid"),
            (outstanding == 0, "paid"),
            (net_paid > 0, "partial"),
            else_="unpaid",
        )
        q = q.where(state == payment_status)
    return invoice_outs(db, list(db.scalars(q.limit(limit).offset(offset))))


@router.get("/jobs/{job_id}/invoices")
def job_invoices(job_id: UUID, _: User = Depends(require("billing.read")), db: DbSession = Depends(get_db, scope="function")):
    get_job(db, job_id)
    return invoice_outs(db, list(db.scalars(select(Invoice).where(Invoice.visit_id == job_id).order_by(Invoice.invoice_no))))


@router.get("/invoices/verify")
def verify_invoice_qr(token: str = Query(..., max_length=200), _: User = Depends(require("billing.read")), db: DbSession = Depends(get_db, scope="function")):
    """Authenticates the QR printed on an invoice: valid only if this installation signed it and the total still matches."""
    return invoice_doc.verify_token(db, token)


@router.get("/invoices/{invoice_id}/document")
def invoice_document(invoice_id: UUID, mode: str = Query("detailed", pattern="^(detailed|summary)$"), lang: str = Query("ar", pattern="^(ar|en)$"),
                     _: User = Depends(require("billing.read")), db: DbSession = Depends(get_db, scope="function")):
    """Customer-facing data for the preview and printing. Same invoice, same totals in both modes; never any internal cost."""
    return invoice_doc.build_document(db, _get_invoice(db, invoice_id), mode, lang)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf_file(invoice_id: UUID, request: Request, mode: str = Query("detailed", pattern="^(detailed|summary)$"),
                     lang: str = Query("ar", pattern="^(ar|en)$"), download: bool = False,
                     user: User = Depends(require("billing.read")), db: DbSession = Depends(get_db, scope="function")):
    inv = _get_invoice(db, invoice_id)
    document = invoice_doc.build_document(db, inv, mode, lang)
    data = invoice_pdf.render_pdf(document, invoice_doc.logo_path(db))
    audit(db, user, "invoice.print", "invoice", inv.id, after={"mode": mode, "lang": lang, "format": "pdf"}, ip=client_ip(request))
    name = f"{document['invoice']['number']}-{mode}-{lang}.pdf"
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": f'{"attachment" if download else "inline"}; filename="{name}"', "Cache-Control": "no-store"})


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: UUID, _: User = Depends(require("billing.read")), db: DbSession = Depends(get_db, scope="function")):
    return invoice_out(db, _get_invoice(db, invoice_id))


def _require_draft(inv: Invoice) -> None:
    if inv.status != "draft":
        raise AppError("الفاتورة نهائية ولا يمكن تعديلها، استخدم إشعار دائن أو الإلغاء", 409, "invoice_final")


@router.patch("/invoices/{invoice_id}")
def patch_invoice(invoice_id: UUID, body: InvoicePatch, request: Request,
                  user: User = Depends(require("billing.write")), db: DbSession = Depends(get_db, scope="function")):
    inv = _get_invoice(db, invoice_id, lock=True)
    _require_draft(inv)
    before = {"discount": str(inv.discount), "tax_rate": str(inv.tax_rate)}
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(inv, k, v if v is not None or k in ("due_date", "notes") else getattr(inv, k))
    _recalc(db, inv)
    audit(db, user, "invoice.update", "invoice", inv.id, before=before,
          after={"discount": str(inv.discount), "tax_rate": str(inv.tax_rate)}, ip=client_ip(request))
    return invoice_out(db, inv)


@router.post("/invoices/{invoice_id}/items", status_code=201)
def add_item(invoice_id: UUID, body: ItemIn, request: Request, user: User = Depends(require("billing.write")),
             db: DbSession = Depends(get_db, scope="function")):
    inv = _get_invoice(db, invoice_id, lock=True)
    _require_draft(inv)
    db.add(InvoiceItem(invoice_id=inv.id, kind=body.kind, description=body.description, quantity=body.quantity,
                       unit_price=body.unit_price, amount=to_money(body.quantity * body.unit_price)))
    _recalc(db, inv)
    audit(db, user, "invoice.item_add", "invoice", inv.id, after={"description": body.description}, ip=client_ip(request))
    return invoice_out(db, inv)


@router.delete("/invoices/{invoice_id}/items/{item_id}")
def remove_item(invoice_id: UUID, item_id: int, request: Request, user: User = Depends(require("billing.write")),
                db: DbSession = Depends(get_db, scope="function")):
    inv = _get_invoice(db, invoice_id, lock=True)
    _require_draft(inv)
    item = db.get(InvoiceItem, item_id)
    if not item or item.invoice_id != inv.id:
        raise AppError("البند غير موجود", 404, "not_found")
    db.delete(item)
    _recalc(db, inv)
    audit(db, user, "invoice.item_remove", "invoice", inv.id, before={"description": item.description}, ip=client_ip(request))
    return invoice_out(db, inv)


@router.delete("/invoices/{invoice_id}")
def delete_draft_invoice(invoice_id: UUID, request: Request, user: User = Depends(require("billing.write")),
                         db: DbSession = Depends(get_db, scope="function")):
    """Only an unissued draft can be removed (it never had a number in the books); issued invoices are cancelled, never deleted."""
    inv = _get_invoice(db, invoice_id, lock=True)
    if inv.status != "draft":
        raise AppError("لا يمكن حذف إلا الفاتورة المسودة — الفاتورة الصادرة تُلغى بإشعار", 409, "not_draft")
    if db.scalar(select(func.count()).select_from(Payment).where(Payment.invoice_id == inv.id)) or \
            db.scalar(select(func.count()).select_from(CreditNote).where(CreditNote.invoice_id == inv.id)):
        raise AppError("على الفاتورة مدفوعات أو إشعارات دائنة ولا يمكن حذفها", 409, "has_payments")
    snapshot = {"number": format_number(db, "invoice", inv.invoice_no), "visit_id": str(inv.visit_id), "total": str(inv.total),
                "items": [i.description for i in db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id))]}
    for item in list(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id))):
        db.delete(item)
    db.flush()
    db.delete(inv)
    audit(db, user, "invoice.delete_draft", "invoice", inv.id, before=snapshot, ip=client_ip(request))
    return {"deleted": True}


@router.post("/invoices/{invoice_id}/issue")
def issue_invoice(invoice_id: UUID, request: Request, user: User = Depends(require("billing.write")),
                  db: DbSession = Depends(get_db, scope="function")):
    visit_id = _get_invoice(db, invoice_id).visit_id
    get_job(db, visit_id, lock=True)
    inv = _get_invoice(db, invoice_id, lock=True)
    _require_draft(inv)
    if not Decimal(inv.subtotal) and not db.scalar(select(InvoiceItem.id).where(
        InvoiceItem.invoice_id == inv.id,
        (InvoiceItem.operation_id.is_not(None) | InvoiceItem.part_id.is_not(None)),
    ).limit(1)):
        raise AppError("الفاتورة فارغة", 422, "empty_invoice")
    now = datetime.now(timezone.utc)
    inv.status, inv.issued_at, inv.invoice_date = "issued", now, inv.invoice_date or now.date()
    inv.doc_snapshot = {"workshop": cfg.get_section(db, "workshop"), "currency": inv.currency,
                        "payment_methods": {m["key"]: m["label"] for m in cfg.get_section(db, "finance")["payment_methods"]}}
    deposits = db.scalars(select(Payment).where(Payment.visit_id == inv.visit_id, Payment.invoice_id.is_(None),
                                                Payment.kind == "deposit"))
    applied = 0
    for d in deposits:  # earlier deposits for this job now count toward this invoice
        d.invoice_id = inv.id
        applied += 1
    audit(db, user, "invoice.issue", "invoice", inv.id, after={"total": str(inv.total), "deposits_applied": applied},
          ip=client_ip(request))
    db.flush()
    return invoice_out(db, inv)


@router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice(invoice_id: UUID, body: ReasonIn, request: Request,
                   user: User = Depends(require("billing.refund")), db: DbSession = Depends(get_db, scope="function")):
    inv = _get_invoice(db, invoice_id, lock=True)
    if inv.status == "cancelled":
        raise AppError("الفاتورة ملغاة بالفعل", 409, "already_cancelled")
    if inv.status == "issued" and db.get(VehicleVisit, inv.visit_id).status == "delivered":
        raise AppError("لا يمكن إلغاء فاتورة أمر تم تسليمه؛ أصدر إشعاراً دائناً أو أعد فتح الأمر أولاً", 409, "delivered_invoice")
    st = money_state(db, inv)
    if st["net_paid"] != 0:
        raise AppError("يوجد مبالغ مدفوعة، سجّل استرداد لها أولاً", 409, "has_payments")
    inv.status, inv.cancelled_at, inv.cancel_reason = "cancelled", datetime.now(timezone.utc), body.reason
    audit(db, user, "invoice.cancel", "invoice", inv.id, reason=body.reason, ip=client_ip(request))
    return invoice_out(db, inv)


# ---- payments ---------------------------------------------------------------------
class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: str
    reference: str | None = None
    note: str | None = None
    idempotency_key: str | None = Field(None, max_length=100)


def _pay_out(p: Payment) -> dict:
    return {"id": p.id, "kind": p.kind, "invoice_id": str(p.invoice_id) if p.invoice_id else None,
            "amount": f"{Decimal(p.amount):.2f}", "method": p.method, "reference": p.reference, "paid_at": p.paid_at}


def _replay(p: Payment, body: PaymentIn, invoice_id, visit_id) -> dict:
    expected_kind = "deposit" if invoice_id is None else "payment"
    if (p.kind != expected_kind or p.amount != body.amount or p.visit_id != visit_id
            or (expected_kind == "payment" and p.invoice_id != invoice_id)
            or p.method != body.method or p.reference != body.reference or p.note != body.note):
        raise AppError("مفتاح التكرار مستخدم لعملية مختلفة", 409, "key_reused")
    return _pay_out(p)


@router.post("/invoices/{invoice_id}/payments", status_code=201)
def record_payment(invoice_id: UUID, body: PaymentIn, request: Request,
                   idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=100),
                   user: User = Depends(require("billing.write")), db: DbSession = Depends(get_db, scope="function")):
    key = idempotency_key or body.idempotency_key
    inv = _get_invoice(db, invoice_id, lock=True)  # lock first: concurrent duplicates serialise here
    prior = _idempotent(db, Payment, key)
    if prior:
        return _replay(prior, body, inv.id, inv.visit_id)
    if body.method not in cfg.payment_method_keys(db):
        raise AppError("طريقة الدفع غير معروفة", 422, "bad_method")
    if inv.status != "issued":
        raise AppError("يمكن تسجيل الدفع على فاتورة صادرة فقط", 409, "not_issued")
    outstanding = money_state(db, inv)["outstanding"]
    if body.amount > outstanding:
        raise AppError(f"المبلغ أكبر من المتبقي ({outstanding})", 422, "overpayment")
    p = Payment(visit_id=inv.visit_id, invoice_id=inv.id, kind="payment", amount=body.amount, method=body.method,
                reference=body.reference, note=body.note, idempotency_key=key, received_by=user.id)
    db.add(p)
    db.flush()
    audit(db, user, "payment.create", "payment", p.id, after={"invoice": inv.invoice_no, "amount": f"{Decimal(p.amount):.2f}",
                                                             "method": p.method}, ip=client_ip(request))
    return _pay_out(p)


@router.post("/jobs/{job_id}/deposits", status_code=201)
def record_deposit(job_id: UUID, body: PaymentIn, request: Request,
                   idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=100),
                   user: User = Depends(require("billing.write")), db: DbSession = Depends(get_db, scope="function")):
    """Money taken before an invoice exists; it is attached to the invoice when that is issued."""
    key = idempotency_key or body.idempotency_key
    job = get_job(db, job_id, lock=True)
    prior = _idempotent(db, Payment, key)
    if prior:
        return _replay(prior, body, None, job.id)
    if body.method not in cfg.payment_method_keys(db):
        raise AppError("طريقة الدفع غير معروفة", 422, "bad_method")
    require_open(job)
    if db.scalar(select(Invoice.id).where(Invoice.visit_id == job.id, Invoice.status == "issued")):
        raise AppError("صدرت فاتورة لهذا الأمر، سجّل الدفعة عليها", 409, "invoice_exists")
    p = Payment(visit_id=job.id, invoice_id=None, kind="deposit", amount=body.amount, method=body.method,
                reference=body.reference, note=body.note, idempotency_key=key, received_by=user.id)
    db.add(p)
    db.flush()
    audit(db, user, "deposit.create", "payment", p.id, after={"job": job.visit_no, "amount": f"{Decimal(p.amount):.2f}"}, ip=client_ip(request))
    return _pay_out(p)


@router.get("/jobs/{job_id}/deposits")
def job_deposits(job_id: UUID, _: User = Depends(require("billing.read")), db: DbSession = Depends(get_db, scope="function")):
    get_job(db, job_id)
    return [_pay_out(p) for p in db.scalars(select(Payment).where(Payment.visit_id == job_id, Payment.kind == "deposit").order_by(Payment.id))]


class RefundIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reason: str = Field(min_length=3)


@router.post("/payments/{payment_id}/refunds", status_code=201)
def refund_payment(payment_id: int, body: RefundIn, request: Request, user: User = Depends(require("billing.refund")),
                   db: DbSession = Depends(get_db, scope="function")):
    p = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if not p:
        raise AppError("الدفعة غير موجودة", 404, "not_found")
    already = _sum(db, Refund.amount, Refund.payment_id == p.id)
    if body.amount > Decimal(p.amount) - already:
        raise AppError(f"أقصى مبلغ يمكن استرداده {Decimal(p.amount) - already}", 422, "too_much")
    r = Refund(payment_id=p.id, amount=body.amount, reason=body.reason, refunded_by=user.id)
    db.add(r)
    db.flush()
    audit(db, user, "refund.create", "refund", r.id, after={"payment": p.id, "amount": f"{Decimal(r.amount):.2f}"}, reason=body.reason,
          ip=client_ip(request))
    return {"id": r.id, "payment_id": p.id, "amount": f"{Decimal(r.amount):.2f}", "refunded_at": r.refunded_at}


# ---- credit notes -----------------------------------------------------------------------
class CreditIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reason: str = Field(min_length=3)


@router.post("/invoices/{invoice_id}/credit-notes", status_code=201)
def create_credit_note(invoice_id: UUID, body: CreditIn, request: Request,
                       user: User = Depends(require("billing.refund")), db: DbSession = Depends(get_db, scope="function")):
    inv = _get_invoice(db, invoice_id, lock=True)
    if inv.status != "issued":
        raise AppError("إشعار الدائن يكون على فاتورة صادرة فقط", 409, "not_issued")
    credited = _sum(db, CreditNote.amount, CreditNote.invoice_id == inv.id)
    if body.amount > Decimal(inv.total) - credited:
        raise AppError(f"أقصى مبلغ لإشعار الدائن {Decimal(inv.total) - credited}", 422, "too_much")
    c = CreditNote(invoice_id=inv.id, amount=body.amount, reason=body.reason, created_by=user.id)
    db.add(c)
    db.flush()
    audit(db, user, "credit_note.create", "credit_note", c.id, after={"invoice": inv.invoice_no, "amount": f"{Decimal(c.amount):.2f}"},
          reason=body.reason, ip=client_ip(request))
    return invoice_out(db, inv)


@router.post("/credit-notes/{credit_id}/cancel")
def cancel_credit_note(credit_id: int, body: ReasonIn, request: Request,
                       user: User = Depends(require("billing.refund")), db: DbSession = Depends(get_db, scope="function")):
    credit = db.get(CreditNote, credit_id)
    if not credit:
        raise AppError("إشعار الدائن غير موجود", 404, "not_found")
    inv = _get_invoice(db, credit.invoice_id, lock=True)
    prior = db.scalar(select(AuditLog.id).where(AuditLog.action == "credit_note.cancel",
                      AuditLog.entity_type == "credit_note", AuditLog.entity_id == str(credit.id)))
    if prior:
        return invoice_out(db, inv)
    if credit.amount <= 0 or inv.status not in ("issued", "cancelled"):
        raise AppError("لا يمكن إلغاء هذا القيد", 409, "invalid_credit_cancellation")
    # Append a signed reversal; never erase the original credit or invent a refund.
    reversal = CreditNote(invoice_id=inv.id, amount=-credit.amount,
                          reason=f"إلغاء {format_number(db, 'credit', credit.credit_no)}: {body.reason}", created_by=user.id)
    db.add(reversal)
    db.flush()
    audit(db, user, "credit_note.cancel", "credit_note", credit.id,
          before={"amount": f"{Decimal(credit.amount):.2f}", "reason": credit.reason},
          after={"reversal_id": reversal.id, "amount": f"{Decimal(reversal.amount):.2f}", "invoice": inv.invoice_no},
          reason=body.reason, ip=client_ip(request))
    db.flush()
    return invoice_out(db, inv)
