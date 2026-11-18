"""Quality control and vehicle delivery with readiness checks and audited manager overrides."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.billing import money_state, unbilled_work
from app.api.deps import client_ip, require
from app.api.jobs import add_history, get_job
from app.api.settings_api import format_number
from app.core.audit import audit
from app.core.errors import AppError
from app.db import get_db
from app.models import (Customer, Delivery, Invoice, MaintenanceReminder, PartPurchase, QualityCheck,
                        RepairOperation, Vehicle, VehicleVisit, Warranty)
from app.models.auth import User
from app.services.pricing import add_months
from app.services.templates import CLOSED, SERVICE_INTERVALS

router = APIRouter(prefix="/api", tags=["delivery"])


def _latest_qc(db: DbSession, job_id) -> QualityCheck | None:
    return db.scalar(select(QualityCheck).where(QualityCheck.visit_id == job_id).order_by(QualityCheck.id.desc()))


def work_blockers(db: DbSession, job: VehicleVisit) -> list[dict]:
    out = []
    ops = [o for o in db.scalars(select(RepairOperation).where(RepairOperation.visit_id == job.id))
           if o.status not in ("done", "cancelled")]
    if ops:
        out.append({"code": "operations_unfinished", "message": f"{len(ops)} عملية صيانة لم تنتهِ"})
    parts = [p for p in db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job.id))
             if p.status not in ("installed", "returned", "cancelled")]
    if parts:
        out.append({"code": "parts_not_installed", "message": f"{len(parts)} قطعة غيار لم تُركّب أو تُرجع"})
    return out


def delivery_blockers(db: DbSession, job: VehicleVisit, lock_invoice: bool = False) -> tuple[list[dict], dict]:
    blockers = work_blockers(db, job)
    qc = _latest_qc(db, job.id)
    if not qc or qc.result != "passed":
        blockers.append({"code": "quality_not_passed", "message": "لم يتم اعتماد فحص الجودة"})
    if job.status != "ready":
        blockers.append({"code": "not_ready", "message": "حالة الأمر ليست «جاهزة للتسليم»"})
    invoice_query = select(Invoice).where(Invoice.visit_id == job.id, Invoice.status == "issued")
    invoices = list(db.scalars(invoice_query.order_by(Invoice.invoice_no).with_for_update() if lock_invoice else invoice_query.order_by(Invoice.invoice_no)))
    info = {"invoice_id": None, "payment_status": None, "outstanding": None}
    if not invoices:
        blockers.append({"code": "no_invoice", "message": "لا توجد فاتورة صادرة"})
    else:
        states = [money_state(db, inv) for inv in invoices]
        # Overpayment on one invoice cannot silently pay another invoice.
        outstanding = sum((max(st["outstanding"], Decimal("0.00")) for st in states), Decimal("0.00"))
        info = {"invoice_id": str(invoices[-1].id), "invoice_ids": [str(i.id) for i in invoices],
                "payment_status": "unpaid" if outstanding > 0 else "paid", "outstanding": str(outstanding)}
        if outstanding > 0:
            blockers.append({"code": "unpaid", "message": f"المتبقي على العميل {outstanding}"})
    operations, parts = unbilled_work(db, job.id)
    info["unbilled"] = {"operations": len(operations), "parts": len(parts)}
    if invoices and (operations or parts):
        blockers.append({"code": "unbilled_items", "message": "توجد إصلاحات أو قطع غيار لم تصدر لها فاتورة"})
    draft_id = db.scalar(select(Invoice.id).where(Invoice.visit_id == job.id, Invoice.status == "draft")
                         .order_by(Invoice.invoice_no).limit(1))
    info["draft_invoice_id"] = str(draft_id) if draft_id else None
    if draft_id:
        blockers.append({"code": "draft_invoice", "message": "توجد فاتورة مسودة لم تصدر بعد"})
    return blockers, info


@router.get("/jobs/{job_id}/delivery-readiness")
def readiness(job_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    blockers, info = delivery_blockers(db, job)
    qc = _latest_qc(db, job.id)
    return {"ready": not blockers, "blockers": blockers, "unbilled": info.pop("unbilled"),
            "draft_invoice_id": info.pop("draft_invoice_id"), "invoice": info,
            "latest_quality_check": ({"result": qc.result, "checked_at": qc.checked_at, "notes": qc.notes} if qc else None)}


# ---- quality check ------------------------------------------------------------------
class QCIn(BaseModel):
    result: str = Field(pattern="^(passed|failed)$")
    repairs_verified: bool = False
    parts_verified: bool = False
    road_test_ok: bool = False
    notes: str | None = None
    override_reason: str | None = None


@router.post("/jobs/{job_id}/quality-check", status_code=201)
def quality_check(job_id: UUID, body: QCIn, request: Request, user: User = Depends(require("qc.write")),
                  db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id, lock=True)
    if job.status in CLOSED:
        raise AppError("أمر الصيانة مغلق", 409, "job_closed")
    notes = (body.notes or "").strip() or None
    override = (body.override_reason or "").strip() or None
    if body.result == "failed":
        if not notes:
            raise AppError("اكتب سبب رفض فحص الجودة", 422, "notes_required")
    else:
        if not (body.repairs_verified and body.parts_verified and body.road_test_ok):
            raise AppError("أكّد مراجعة الأعمال والقطع وتجربة العربية", 422, "checklist_incomplete")
        blockers = work_blockers(db, job)
        if blockers:
            if not override or "jobs.override" not in user.permissions:
                raise AppError("; ".join(b["message"] for b in blockers), 422, "work_unfinished")
    qc = QualityCheck(visit_id=job.id, result=body.result, repairs_verified=body.repairs_verified,
                      parts_verified=body.parts_verified, road_test_ok=body.road_test_ok, notes=notes,
                      override_reason=override if body.result == "passed" else None, checked_by=user.id)
    db.add(qc)
    new = "ready" if body.result == "passed" else "in_progress"  # failed = rework
    if body.result == "failed":
        job.completed_at = None
    if job.status != new:
        add_history(db, job, new, user, "فحص الجودة: " + ("اجتاز" if new == "ready" else f"فشل - {notes}"), job.status)
        job.status = new
        if new == "ready" and not job.completed_at:
            job.completed_at = datetime.now(timezone.utc)
    db.flush()
    audit(db, user, "qc." + body.result, "job", job.id, after={"notes": notes, "override": override}, ip=client_ip(request))
    return {"id": qc.id, "result": qc.result, "job_status": job.status}


# ---- delivery ---------------------------------------------------------------------------
class DeliverIn(BaseModel):
    final_mileage: int = Field(ge=0)
    final_condition: str | None = None
    ack_name: str = Field(min_length=2, max_length=200)  # who received the car (customer acknowledgment)
    ack_note: str | None = None
    override_reason: str | None = None


@router.post("/jobs/{job_id}/deliver")
def deliver(job_id: UUID, body: DeliverIn, request: Request, user: User = Depends(require("delivery.write")),
            db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id, lock=True)
    if job.status in CLOSED:
        raise AppError("أمر الصيانة مغلق بالفعل", 409, "job_closed")
    if job.mileage is not None and body.final_mileage < job.mileage:
        raise AppError("قراءة العداد عند التسليم أقل من قراءة الاستلام", 422, "bad_mileage")
    blockers, info = delivery_blockers(db, job, lock_invoice=True)
    # Issued invoice is mandatory even for a manager exception. Serialize with cancellation.
    db.refresh(job)
    if job.status in CLOSED:
        raise AppError("أمر الصيانة مغلق بالفعل", 409, "job_closed")
    if not info["invoice_id"] or any(b["code"] in {"draft_invoice", "unbilled_items"} for b in blockers):
        raise AppError("لا يمكن التسليم وإغلاق أمر الشغل قبل إصدار الفاتورة: " + "; ".join(b["message"] for b in blockers), 409, "invoice_required")
    override = (body.override_reason or "").strip() or None
    if blockers:
        if "jobs.override" not in user.permissions or not override:
            raise AppError("لا يمكن التسليم: " + "; ".join(b["message"] for b in blockers), 409, "not_deliverable")
        # the override itself is a deliberate, audited manager decision
    now = datetime.now(timezone.utc)
    frm = job.status
    job.status, job.delivered_at = "delivered", now
    job.completed_at = job.completed_at or now
    add_history(db, job, "delivered", user, override and f"تسليم باستثناء إداري: {override}", frm)
    d = Delivery(visit_id=job.id, delivered_at=now, final_mileage=body.final_mileage, final_condition=body.final_condition,
                 ack_name=body.ack_name.strip(), ack_note=body.ack_note,
                 invoice_id=UUID(info["invoice_id"]) if info["invoice_id"] else None, payment_status=info["payment_status"],
                 overridden={"blockers": [b["code"] for b in blockers]} if blockers else None,
                 override_reason=override if blockers else None, delivered_by=user.id)
    db.add(d)
    v = db.get(Vehicle, job.vehicle_id)
    if (v.current_mileage or 0) < body.final_mileage:
        v.current_mileage = body.final_mileage
    created = _create_reminders(db, job, body.final_mileage, user)
    audit(db, user, "delivery.override" if blockers else "delivery.complete", "job", job.id,
          after={"final_mileage": body.final_mileage, "ack": body.ack_name, "blockers": [b["code"] for b in blockers],
                 "reminders": created}, reason=override if blockers else None, ip=client_ip(request))
    db.flush()
    return {"job_id": str(job.id), "status": job.status, "delivered_at": job.delivered_at,
            "overridden": [b["code"] for b in blockers], "reminders_created": created}


def _create_reminders(db: DbSession, job: VehicleVisit, mileage: int, user: User) -> int:
    cats = {o.category for o in db.scalars(select(RepairOperation).where(
        RepairOperation.visit_id == job.id, RepairOperation.status == "done")) if o.category in SERVICE_INTERVALS}
    today = datetime.now(timezone.utc).date()
    n = 0
    for cat in sorted(cats):
        months, km, title = SERVICE_INTERVALS[cat]
        for old in db.scalars(select(MaintenanceReminder).where(
                MaintenanceReminder.vehicle_id == job.vehicle_id, MaintenanceReminder.category == cat,
                MaintenanceReminder.status == "open")):
            old.status, old.completed_at = "done", datetime.now(timezone.utc)  # this service satisfies the old reminder
        db.add(MaintenanceReminder(vehicle_id=job.vehicle_id, title=title, category=cat, source_visit_id=job.id,
                                   due_date=add_months(today, months) if months else None,
                                   due_mileage=mileage + km if km else None, created_by=user.id))
        n += 1
    return n


@router.get("/jobs/{job_id}/delivery-report")
def delivery_report(job_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    d = db.scalar(select(Delivery).where(Delivery.visit_id == job.id).order_by(Delivery.id.desc()))
    if not d:
        raise AppError("لم يتم تسليم هذا الأمر بعد", 404, "not_delivered")
    v, c = db.get(Vehicle, job.vehicle_id), db.get(Customer, job.customer_id)
    ops = db.scalars(select(RepairOperation).where(RepairOperation.visit_id == job.id, RepairOperation.status != "cancelled")
                     .order_by(RepairOperation.id))
    parts = db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job.id, PartPurchase.status == "installed")
                       .order_by(PartPurchase.id))
    qc = _latest_qc(db, job.id)
    invoices = db.scalars(select(Invoice).where(
        Invoice.visit_id == job.id,
        or_(Invoice.id == d.invoice_id, Invoice.issued_at <= d.delivered_at),
        or_(Invoice.cancelled_at.is_(None), Invoice.cancelled_at > d.delivered_at),
    ).order_by(Invoice.invoice_no))
    invoice_rows = []
    legacy_invoice = None
    for invoice in invoices:
        payment = money_state(db, invoice, at_delivery=d.delivered_at)
        row = {"number": format_number(db, "invoice", invoice.invoice_no), "total": str(invoice.total),
               "currency": invoice.currency, "payment_status": payment["payment_status"],
               "outstanding": str(payment["outstanding"])}
        invoice_rows.append(row)
        if invoice.id == d.invoice_id:
            legacy_invoice = {**row, "payment_status": d.payment_status}
    warranties = db.scalars(select(Warranty).where(Warranty.visit_id == job.id, Warranty.is_void.is_(False)))
    return {"job_no": job.visit_no, "arrival_at": job.arrival_at, "delivered_at": d.delivered_at,
            "customer": {"name": c.full_name, "mobile": c.mobile},
            "vehicle": {"make": v.make, "model": v.model, "plate": job.plate_at_visit},
            "arrival_mileage": job.mileage, "final_mileage": d.final_mileage, "final_condition": d.final_condition,
            "operations": [{"description": o.description, "status": o.status} for o in ops],
            "installed_parts": [{"name": p.part_name, "brand": p.brand, "part_number": p.part_number} for p in parts],
            "quality_check": {"result": qc.result, "at": qc.checked_at, "notes": qc.notes} if qc else None,
            "invoice": legacy_invoice, "invoices": invoice_rows,
            "warranties": [{"description": w.description, "end_date": w.end_date, "mileage_limit": w.mileage_limit}
                           for w in warranties],
            "acknowledged_by": d.ack_name, "ack_note": d.ack_note,
            "overridden": d.overridden, "override_reason": d.override_reason}
