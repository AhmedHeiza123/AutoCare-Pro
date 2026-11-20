"""Suppliers and externally purchased parts (no inventory: records per job only)."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.api.jobs import get_job, recompute_total, require_open
from app.api.warranty import create_part_warranty
from app.core.audit import audit
from app.services import settings as cfg
from app.services.job_status import sync_work_status
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (PartPurchase, PartReturn, RepairOperation, Supplier, Technician, Vehicle,
                        VehicleVisit)
from app.models.auth import User
from app.services.work_approval import require_work_approval
from app.models import StockReservation
from app.services import inventory as inv_svc
from app.services.accounting import billed_quantity
from app.services.pricing import add_months, effective_qty, line_cost, line_price, returned_for_parts, returned_qty

router = APIRouter(prefix="/api", tags=["parts"])

FLOW = ["requested", "ordered", "purchased", "received", "installed"]
TERMINAL = {"returned", "cancelled"}


# ---- suppliers ---------------------------------------------------------------
class SupplierIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None


class SupplierPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool | None = None


def sup_out(s: Supplier) -> dict:
    return {"id": s.id, "name": s.name, "contact_person": s.contact_person, "phone": s.phone, "email": s.email,
            "address": s.address, "notes": s.notes, "is_active": s.is_active}


@router.get("/suppliers")
def list_suppliers(q: str | None = None, active: bool | None = None, _: User = Depends(require("visits.read")),
                   db: DbSession = Depends(get_db, scope="function")):
    stmt = select(Supplier).order_by(Supplier.name)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))
    if active is not None:
        stmt = stmt.where(Supplier.is_active == active)
    return [sup_out(s) for s in db.scalars(stmt)]


@router.post("/suppliers", status_code=201)
def create_supplier(body: SupplierIn, request: Request, user: User = Depends(require("suppliers.write")),
                    db: DbSession = Depends(get_db, scope="function")):
    if db.scalar(select(Supplier.id).where(func.lower(Supplier.name) == body.name.lower())):
        raise AppError("المورد مسجل من قبل", 409, "duplicate_supplier")
    s = Supplier(**body.model_dump())
    db.add(s)
    db.flush()
    audit(db, user, "supplier.create", "supplier", s.id, after=sup_out(s), ip=client_ip(request))
    return sup_out(s)


@router.patch("/suppliers/{sid}")
def update_supplier(sid: int, body: SupplierPatch, request: Request,
                    user: User = Depends(require("suppliers.write")), db: DbSession = Depends(get_db, scope="function")):
    s = db.get(Supplier, sid)
    if not s:
        raise AppError("المورد غير موجود", 404, "not_found")
    before = sup_out(s)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    audit(db, user, "supplier.update", "supplier", s.id, before=before, after=sup_out(s), ip=client_ip(request))
    return sup_out(s)


# ---- parts ----------------------------------------------------------------------
class PartIn(BaseModel):
    part_name: str = Field(min_length=2, max_length=200)
    category: str | None = None
    brand: str | None = None
    part_number: str | None = None
    supplier_id: int | None = None
    supplier_invoice_no: str | None = None
    operation_id: int | None = None
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit_cost: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    unit_price: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    warranty_months: int | None = Field(None, ge=0, le=240)
    status: str = "requested"
    purchased_at: datetime | None = None
    notes: str | None = None


class PartPatch(BaseModel):
    part_name: str | None = Field(None, min_length=2)
    brand: str | None = None
    part_number: str | None = None
    supplier_id: int | None = None
    supplier_invoice_no: str | None = None
    quantity: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    unit_cost: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    unit_price: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    warranty_months: int | None = Field(None, ge=0, le=240)
    notes: str | None = None


class PartStatusIn(BaseModel):
    status: str
    technician_id: int | None = None


class ReturnIn(BaseModel):
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    refund_amount: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    reason: str = Field(min_length=2)


def part_out(db: DbSession, p: PartPurchase, user: User, ret: dict | None = None) -> dict:
    """`ret` = returned quantities from returned_for_parts(); pass it when serialising many parts (avoids ~5 queries per part)."""
    eff = effective_qty(db, p, ret)
    given = returned_qty(db, p.id) if ret is None else ret.get(p.id, Decimal("0"))
    d = {"id": p.id, "visit_id": str(p.visit_id), "operation_id": p.operation_id, "supplier_id": p.supplier_id,
         "part_name": p.part_name, "category": p.category, "brand": p.brand, "part_number": p.part_number,
         "supplier_invoice_no": p.supplier_invoice_no, "status": p.status, "purchased_at": p.purchased_at,
         "quantity": str(p.quantity), "returned_quantity": str(given), "effective_quantity": str(eff),
         "unit_price": str(p.unit_price), "total_price": str(line_price(db, p, ret)), "installed_at": p.installed_at,
         "installed_by": p.installed_by, "warranty_months": p.warranty_months,
         "warranty_expiry": p.warranty_expiry, "notes": p.notes,
         "source": p.source, "inventory_item_id": p.inventory_item_id, "warehouse_id": p.warehouse_id, "issued_qty": str(p.issued_qty)}
    if p.source == "warehouse":  # stock held for this part right now (None once issued / released)
        held = db.scalar(select(StockReservation.qty).where(StockReservation.part_id == p.id, StockReservation.status == "active"))
        d["reserved_qty"] = str(held) if held is not None else None
    if "parts.costs" in user.permissions:  # purchase cost and profit are not for every role
        d["unit_cost"] = str(p.unit_cost)
        d["total_cost"] = str(line_cost(db, p, ret))
        d["gross_profit"] = str(line_price(db, p, ret) - line_cost(db, p, ret))
    return d


def _validate_links(db: DbSession, job: VehicleVisit, supplier_id, operation_id) -> None:
    if supplier_id is not None:
        s = db.get(Supplier, supplier_id)
        if not s or not s.is_active:
            raise AppError("المورد غير موجود أو غير مفعل", 422, "bad_supplier")
    if operation_id is not None:
        op = db.get(RepairOperation, operation_id)
        if not op or op.visit_id != job.id:
            raise AppError("العملية لا تخص هذا الأمر", 422, "bad_operation")


@router.post("/jobs/{job_id}/parts", status_code=201)
def add_part(job_id: UUID, body: PartIn, request: Request, force: bool = False,
             user: User = Depends(require("parts.write")), db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id, lock=True)
    require_open(job)
    if body.status not in FLOW[:4]:
        raise AppError("الحالة الابتدائية غير صحيحة (التركيب يتم لاحقاً)", 422, "bad_status")
    _validate_links(db, job, body.supplier_id, body.operation_id)
    if body.supplier_invoice_no and body.part_number and not force:  # same part/invoice twice = likely double entry
        dup = db.scalar(select(PartPurchase).where(
            PartPurchase.visit_id == job.id, PartPurchase.supplier_id == body.supplier_id,
            PartPurchase.supplier_invoice_no == body.supplier_invoice_no,
            PartPurchase.part_number == body.part_number, PartPurchase.status != "cancelled"))
        if dup:
            return JSONResponse(status_code=409, content=jsonable_encoder({
                "error": "possible_duplicate", "message": "القطعة دي مسجلة بنفس فاتورة المورد على نفس الأمر",
                "existing_id": dup.id}))
    data = body.model_dump()
    if data["warranty_months"] is None:
        default = int(cfg.get_section(db, "warranty")["default_part_months"])
        data["warranty_months"] = default or None
    p = PartPurchase(visit_id=job.id, created_by=user.id, **data)
    if p.status in ("purchased", "received") and not p.purchased_at:
        p.purchased_at = datetime.now(timezone.utc)
    db.add(p)
    db.flush()
    recompute_total(db, job)
    audit(db, user, "part.create", "part", p.id, after=part_out(db, p, user), ip=client_ip(request))
    sync_work_status(db, job, user, "تلقائي: تمت إضافة قطعة غيار", client_ip(request))
    return part_out(db, p, user)


@router.get("/jobs/{job_id}/parts")
def job_parts(job_id: UUID, user: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    rows = list(db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job.id).order_by(PartPurchase.id)))
    ret = returned_for_parts(db, [p.id for p in rows])
    return [part_out(db, p, user, ret) for p in rows]


@router.get("/parts")
def search_parts(q: str | None = None, supplier_id: int | None = None, status: str | None = None,
                 limit: int = Query(50, le=200), user: User = Depends(require("visits.read")),
                 db: DbSession = Depends(get_db, scope="function")):
    stmt = select(PartPurchase, VehicleVisit.visit_no, Vehicle.plate) \
        .join(VehicleVisit, VehicleVisit.id == PartPurchase.visit_id) \
        .join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(PartPurchase.part_number.ilike(like), PartPurchase.part_name.ilike(like),
                              PartPurchase.brand.ilike(like)))
    if supplier_id:
        stmt = stmt.where(PartPurchase.supplier_id == supplier_id)
    if status:
        stmt = stmt.where(PartPurchase.status == status)
    rows = db.execute(stmt.order_by(PartPurchase.id.desc()).limit(limit)).all()
    ret = returned_for_parts(db, [p.id for p, _, _ in rows])
    return [{**part_out(db, p, user, ret), "job_no": no, "plate": plate} for p, no, plate in rows]


def _get_part(db: DbSession, part_id: int) -> tuple[PartPurchase, VehicleVisit]:
    p = db.get(PartPurchase, part_id)
    if not p:
        raise AppError("القطعة غير موجودة", 404, "not_found")
    job = get_job(db, p.visit_id, lock=True)
    db.refresh(p)
    return p, job


@router.patch("/parts/{part_id}")
def update_part(part_id: int, body: PartPatch, request: Request, user: User = Depends(require("parts.write")),
                db: DbSession = Depends(get_db, scope="function")):
    p, job = _get_part(db, part_id)
    require_open(job)
    if p.status in TERMINAL or p.status == "installed":
        raise AppError("لا يمكن تعديل قطعة تم تركيبها أو إرجاعها أو إلغاؤها", 409, "part_locked")
    ch = body.model_dump(exclude_unset=True)
    if "supplier_id" in ch:
        _validate_links(db, job, ch["supplier_id"], None)
    billed = billed_quantity(db, p.id)
    if billed > 0:  # on an issued invoice: history (revenue and COGS) must not change retroactively
        repriced = any(k in ch and ch[k] is not None and Decimal(ch[k]) != Decimal(getattr(p, k)) for k in ("unit_cost", "unit_price"))
        if repriced or ("quantity" in ch and ch["quantity"] is not None and Decimal(ch["quantity"]) < billed):
            raise AppError("القطعة مدرجة في فاتورة صادرة؛ لا يمكن تغيير التكلفة أو السعر أو تقليل الكمية — استخدم إشعاراً دائناً أو المرتجع",
                           409, "part_invoiced")
    if p.source == "warehouse":
        if "unit_cost" in ch and ch["unit_cost"] is not None and Decimal(ch["unit_cost"]) != Decimal(p.unit_cost):
            raise AppError("تكلفة قطعة المخزن تُحسب من المخزن (المتوسط المرجّح) ولا تُعدّل يدويًا", 409, "cost_from_inventory")
        if "quantity" in ch and ch["quantity"] is not None and Decimal(ch["quantity"]) != Decimal(p.quantity) and Decimal(p.issued_qty) > 0:
            raise AppError("القطعة صُرفت من المخزن؛ أضف سطرًا جديدًا أو سجّل مرتجعًا بدل تغيير الكمية", 409, "already_issued")
    elif p.source == "customer":
        for k in ("unit_cost", "unit_price"):
            if k in ch and ch[k] is not None and Decimal(ch[k]) != 0:
                raise AppError("قطعة العميل بلا سعر ولا تكلفة", 409, "customer_part_free")
    before = part_out(db, p, user)
    for k, v in ch.items():
        setattr(p, k, v)
    if p.source == "warehouse" and "quantity" in ch and inv_svc.active_reservation(db, p.id) is not None:
        inv_svc.sync_reservation(db, p, user, "quantity changed")  # the held stock follows the new quantity
    recompute_total(db, job)
    audit(db, user, "part.update", "part", p.id, before=before, after=part_out(db, p, user), ip=client_ip(request))
    return part_out(db, p, user)


@router.post("/parts/{part_id}/status")
def part_status(part_id: int, body: PartStatusIn, request: Request, user: User = Depends(require("parts.write")),
                db: DbSession = Depends(get_db, scope="function")):
    p, job = _get_part(db, part_id)
    require_open(job)
    to, frm = body.status, p.status
    if frm in TERMINAL:
        raise AppError("حالة القطعة نهائية", 409, "part_final")
    if to == "returned":
        raise AppError("استخدم عملية الإرجاع لتسجيل المرتجع", 422, "use_return")
    if to == "cancelled":
        if frm == "installed":
            raise AppError("قطعة مركبة لا تُلغى، سجّل مرتجع", 409, "installed_part")
        if billed_quantity(db, p.id) > 0:  # the customer was billed for it: cancelling would leave revenue without a part
            raise AppError("القطعة مدرجة في فاتورة صادرة ولا يمكن إلغاؤها؛ سجّل مرتجعاً وإشعاراً دائناً", 409, "part_invoiced")
        if p.source == "warehouse" and Decimal(p.issued_qty) > 0:
            raise AppError("القطعة صُرفت من المخزن؛ سجّل إرجاعها للمخزن بدل الإلغاء", 409, "use_warehouse_return")
    elif to not in FLOW:
        raise AppError("حالة غير معروفة", 422, "bad_status")
    elif FLOW.index(to) <= FLOW.index(frm):
        raise AppError("لا يمكن الرجوع لحالة سابقة أو تكرار نفس الحالة", 409, "bad_transition")
    if p.source == "customer" and to in ("ordered", "purchased"):
        raise AppError("قطعة العميل لا تُطلب ولا تُشترى", 409, "customer_part")
    if to in ("ordered", "purchased", "installed") or (to == "received" and p.source == "warehouse"):
        require_work_approval(db, job.id, part_id=p.id, amount=line_price(db, p))  # stock is held/issued only for approved work
    now = datetime.now(timezone.utc)
    before = part_out(db, p, user)
    if to == "installed":
        if p.installed_at:  # never install the same part twice
            raise AppError("القطعة مركبة بالفعل", 409, "already_installed")
        t = db.get(Technician, body.technician_id) if body.technician_id else None
        if not t or not t.is_active:
            raise AppError("اختار الفني اللي ركّب القطعة", 422, "technician_required")
        p.installed_by, p.installed_at = t.id, now
        if p.warranty_months:
            p.warranty_expiry = add_months(now.date(), p.warranty_months)
            create_part_warranty(db, job, p, user)
    if p.source == "warehouse":  # warehouse part: ordered/purchased = stock reserved, received/installed = stock issued, cancelled = released
        if to in ("ordered", "purchased"):
            inv_svc.sync_reservation(db, p, user, "approved for the repair order")
        elif to in ("received", "installed"):
            inv_svc.issue_for_part(db, p, user)
        elif to == "cancelled":
            inv_svc.release(db, p, user, "part cancelled")
    if to in ("purchased", "received") and not p.purchased_at:
        p.purchased_at = now
    p.status = to
    recompute_total(db, job)
    sync_work_status(db, job, user, "تلقائي: تم تحديث حالة قطع الغيار", client_ip(request))
    audit(db, user, "part.status", "part", p.id, before={"status": frm}, after={"status": to}, ip=client_ip(request))
    return part_out(db, p, user)


@router.post("/parts/{part_id}/return")
def return_part(part_id: int, body: ReturnIn, request: Request, user: User = Depends(require("parts.write")),
                db: DbSession = Depends(get_db, scope="function")):
    p, job = _get_part(db, part_id)
    require_open(job)
    if p.status in TERMINAL or p.status in ("requested", "ordered"):
        raise AppError("لا يمكن إرجاع قطعة لم تُشترى أو تم إرجاعها أو إلغاؤها", 409, "not_returnable")
    if p.source == "warehouse":
        raise AppError("قطعة من المخزن: استخدم «إرجاع للمخزن» حتى يعود الرصيد والتكلفة بشكل صحيح", 409, "use_warehouse_return")
    left = effective_qty(db, p)
    if body.quantity > left:
        raise AppError(f"الكمية المتاحة للإرجاع {left}", 422, "too_many")
    before = part_out(db, p, user)
    db.add(PartReturn(part_id=p.id, quantity=body.quantity, refund_amount=body.refund_amount,
                      reason=body.reason, returned_by=user.id))
    db.flush()
    if effective_qty(db, p) == 0:
        p.status = "returned"
    recompute_total(db, job)
    if p.status != before["status"]:
        sync_work_status(db, job, user, "تلقائي: تم إرجاع قطعة غيار", client_ip(request))
    audit(db, user, "part.return", "part", p.id, before=before, after=part_out(db, p, user), reason=body.reason,
          ip=client_ip(request))
    return part_out(db, p, user)


@router.get("/suppliers/{sid}/purchases")
def supplier_purchases(sid: int, user: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    s = db.get(Supplier, sid)
    if not s:
        raise AppError("المورد غير موجود", 404, "not_found")
    parts = list(db.scalars(select(PartPurchase).where(PartPurchase.supplier_id == sid).order_by(PartPurchase.id.desc())))
    ret = returned_for_parts(db, [p.id for p in parts])
    out = {"supplier": sup_out(s), "parts": [part_out(db, p, user, ret) for p in parts]}
    if "parts.costs" in user.permissions:
        out["total_cost"] = str(sum((line_cost(db, p, ret) for p in parts), Decimal("0.00")))
        refunds = db.scalar(select(func.coalesce(func.sum(PartReturn.refund_amount), 0))
                            .join(PartPurchase, PartPurchase.id == PartReturn.part_id).where(PartPurchase.supplier_id == sid))
        out["total_refunds"] = str(to_money(refunds))
    return out
