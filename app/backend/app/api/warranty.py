"""Warranties, warranty claims and maintenance reminders."""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.api.jobs import get_job
from app.core.audit import audit
from app.core.errors import AppError
from app.db import get_db
from app.models import (Customer, MaintenanceReminder, PartPurchase, RepairOperation, Vehicle, VehicleVisit,
                        Warranty, WarrantyClaim)
from app.models.auth import User
from app.services.pricing import add_months

router = APIRouter(prefix="/api", tags=["warranty"])
MILEAGE_SOON_KM = 500
DUE_SOON_DAYS = 14


def _today() -> date:
    return datetime.now(timezone.utc).date()


def create_part_warranty(db: DbSession, job: VehicleVisit, part: PartPurchase, user: User | None) -> Warranty:
    """Called when a part with a warranty period is installed."""
    start = part.installed_at.date() if part.installed_at else _today()
    w = Warranty(visit_id=job.id, vehicle_id=job.vehicle_id, customer_id=job.customer_id, kind="part", part_id=part.id,
                 description=f"ضمان قطعة: {part.part_name}", start_date=start, end_date=part.warranty_expiry or add_months(start, part.warranty_months or 0),
                 start_mileage=job.mileage, created_by=user.id if user else None)
    db.add(w)
    return w


def warranty_status(w: Warranty) -> str:
    if w.is_void:
        return "void"
    return "expired" if w.end_date < _today() else "active"


def w_out(db: DbSession, w: Warranty) -> dict:
    claims = db.scalars(select(WarrantyClaim).where(WarrantyClaim.warranty_id == w.id).order_by(WarrantyClaim.id))
    return {"id": w.id, "visit_id": str(w.visit_id), "vehicle_id": str(w.vehicle_id), "kind": w.kind, "part_id": w.part_id,
            "operation_id": w.operation_id, "description": w.description, "start_date": w.start_date, "end_date": w.end_date,
            "start_mileage": w.start_mileage, "mileage_limit": w.mileage_limit, "coverage": w.coverage,
            "exclusions": w.exclusions, "status": warranty_status(w), "void_reason": w.void_reason,
            "claims": [{"id": c.id, "claim_date": c.claim_date, "mileage": c.mileage, "description": c.description,
                        "status": c.status, "resolution": c.resolution, "repair_visit_id": str(c.repair_visit_id) if c.repair_visit_id else None}
                       for c in claims]}


class WarrantyIn(BaseModel):
    kind: str = Field(pattern="^(labor|operation)$")
    operation_id: int | None = None
    description: str = Field(min_length=2)
    months: int = Field(ge=1, le=240)
    mileage_limit: int | None = Field(None, ge=1)
    coverage: str | None = None
    exclusions: str | None = None


@router.post("/jobs/{job_id}/warranties", status_code=201)
def add_warranty(job_id: UUID, body: WarrantyIn, request: Request, user: User = Depends(require("visits.write")),
                 db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    if body.operation_id is not None:
        op = db.get(RepairOperation, body.operation_id)
        if not op or op.visit_id != job.id:
            raise AppError("العملية لا تخص هذا الأمر", 422, "bad_operation")
    start = _today()
    w = Warranty(visit_id=job.id, vehicle_id=job.vehicle_id, customer_id=job.customer_id, kind=body.kind,
                 operation_id=body.operation_id, description=body.description, start_date=start,
                 end_date=add_months(start, body.months), start_mileage=job.mileage, mileage_limit=body.mileage_limit,
                 coverage=body.coverage, exclusions=body.exclusions, created_by=user.id)
    db.add(w)
    db.flush()
    audit(db, user, "warranty.create", "warranty", w.id, after={"end": w.end_date, "kind": w.kind}, ip=client_ip(request))
    return w_out(db, w)


@router.get("/jobs/{job_id}/warranties")
def job_warranties(job_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    get_job(db, job_id)
    return [w_out(db, w) for w in db.scalars(select(Warranty).where(Warranty.visit_id == job_id).order_by(Warranty.id))]


@router.get("/vehicles/{vehicle_id}/warranties")
def vehicle_warranties(vehicle_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    return [w_out(db, w) for w in db.scalars(select(Warranty).where(Warranty.vehicle_id == vehicle_id).order_by(Warranty.end_date.desc()))]


@router.get("/warranties")
def list_warranties(status: str | None = None, expiring_days: int | None = Query(None, ge=1),
                    _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    rows = list(db.scalars(select(Warranty).order_by(Warranty.end_date)))
    out = []
    for w in rows:
        if status and warranty_status(w) != status:
            continue
        if expiring_days and not (warranty_status(w) == "active" and w.end_date <= _today() + timedelta(days=expiring_days)):
            continue
        v = db.get(Vehicle, w.vehicle_id)
        out.append({**w_out(db, w), "plate": v.plate, "vehicle": f"{v.make} {v.model}"})
    return out


class VoidIn(BaseModel):
    reason: str = Field(min_length=3)


@router.post("/warranties/{wid}/void")
def void_warranty(wid: int, body: VoidIn, request: Request, user: User = Depends(require("warranties.decide")),
                  db: DbSession = Depends(get_db, scope="function")):
    w = db.get(Warranty, wid)
    if not w:
        raise AppError("الضمان غير موجود", 404, "not_found")
    w.is_void, w.void_reason = True, body.reason
    audit(db, user, "warranty.void", "warranty", w.id, reason=body.reason, ip=client_ip(request))
    return w_out(db, w)


class ClaimIn(BaseModel):
    description: str = Field(min_length=3)
    mileage: int | None = Field(None, ge=0)


@router.post("/warranties/{wid}/claims", status_code=201)
def add_claim(wid: int, body: ClaimIn, request: Request, user: User = Depends(require("visits.write")),
              db: DbSession = Depends(get_db, scope="function")):
    w = db.get(Warranty, wid)
    if not w:
        raise AppError("الضمان غير موجود", 404, "not_found")
    if warranty_status(w) != "active":
        raise AppError("الضمان منتهي أو ملغي", 409, "warranty_not_active")
    if w.mileage_limit and body.mileage is not None and w.start_mileage is not None \
            and body.mileage - w.start_mileage > w.mileage_limit:
        raise AppError(f"تجاوزت العربية حد الضمان ({w.mileage_limit} كم)", 409, "mileage_exceeded")
    c = WarrantyClaim(warranty_id=w.id, claim_date=_today(), mileage=body.mileage, description=body.description,
                      created_by=user.id)
    db.add(c)
    db.flush()
    audit(db, user, "warranty.claim", "warranty", w.id, after={"claim": c.id, "description": body.description}, ip=client_ip(request))
    return w_out(db, w)


class DecideIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    resolution: str = Field(min_length=3)
    repair_visit_id: UUID | None = None  # the (repeat-repair) job card that fixes it


@router.post("/claims/{cid}/decide")
def decide_claim(cid: int, body: DecideIn, request: Request, user: User = Depends(require("warranties.decide")),
                 db: DbSession = Depends(get_db, scope="function")):
    c = db.get(WarrantyClaim, cid)
    if not c:
        raise AppError("المطالبة غير موجودة", 404, "not_found")
    if c.status != "open":
        raise AppError("تم البت في المطالبة من قبل", 409, "already_decided")
    w = db.get(Warranty, c.warranty_id)
    if body.repair_visit_id:
        rv = db.get(VehicleVisit, body.repair_visit_id)
        if not rv or rv.vehicle_id != w.vehicle_id:
            raise AppError("أمر الإصلاح لا يخص نفس العربية", 422, "bad_visit")
        c.repair_visit_id = rv.id
    c.status, c.resolution, c.decided_by, c.decided_at = body.decision, body.resolution, user.id, datetime.now(timezone.utc)
    audit(db, user, "warranty.claim_decide", "warranty", w.id, after={"claim": c.id, "decision": body.decision},
          reason=body.resolution, ip=client_ip(request))
    return w_out(db, w)


# ---- maintenance reminders -----------------------------------------------------------------
class ReminderIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    category: str | None = None
    due_date: date | None = None
    due_mileage: int | None = Field(None, ge=0)


def reminder_state(r: MaintenanceReminder, mileage: int | None) -> str:
    if r.status != "open":
        return r.status
    today = _today()
    if (r.due_date and r.due_date < today) or (r.due_mileage and mileage is not None and mileage >= r.due_mileage):
        return "overdue"
    if (r.due_date and r.due_date <= today + timedelta(days=DUE_SOON_DAYS)) or \
            (r.due_mileage and mileage is not None and mileage >= r.due_mileage - MILEAGE_SOON_KM):
        return "due_soon"
    return "upcoming"


def r_out(db: DbSession, r: MaintenanceReminder) -> dict:
    v = db.get(Vehicle, r.vehicle_id)
    c = db.get(Customer, v.current_customer_id) if v.current_customer_id else None
    return {"id": r.id, "vehicle_id": str(v.id), "plate": v.plate, "vehicle": f"{v.make} {v.model}",
            "customer": c.full_name if c else None, "mobile": c.mobile if c else None, "title": r.title,
            "category": r.category, "due_date": r.due_date, "due_mileage": r.due_mileage,
            "current_mileage": v.current_mileage, "status": reminder_state(r, v.current_mileage)}


@router.post("/vehicles/{vehicle_id}/reminders", status_code=201)
def add_reminder(vehicle_id: UUID, body: ReminderIn, request: Request, user: User = Depends(require("visits.write")),
                 db: DbSession = Depends(get_db, scope="function")):
    if not db.get(Vehicle, vehicle_id):
        raise AppError("السيارة غير موجودة", 404, "not_found")
    if body.due_date is None and body.due_mileage is None:
        raise AppError("حدد تاريخاً أو عداداً للتذكير", 422, "no_due")
    r = MaintenanceReminder(vehicle_id=vehicle_id, created_by=user.id, **body.model_dump())
    db.add(r)
    db.flush()
    audit(db, user, "reminder.create", "reminder", r.id, after=body.model_dump(mode="json"), ip=client_ip(request))
    return r_out(db, r)


@router.get("/reminders")
def list_reminders(state: str | None = Query(None, pattern="^(overdue|due_soon|upcoming|done|dismissed)$"),
                   vehicle_id: UUID | None = None, _: User = Depends(require("visits.read")),
                   db: DbSession = Depends(get_db, scope="function")):
    q = select(MaintenanceReminder)
    if vehicle_id:
        q = q.where(MaintenanceReminder.vehicle_id == vehicle_id)
    rows = [r_out(db, r) for r in db.scalars(q.order_by(MaintenanceReminder.due_date.nulls_last(), MaintenanceReminder.id))]
    if state:
        return [r for r in rows if r["status"] == state]
    return [r for r in rows if r["status"] in ("overdue", "due_soon", "upcoming")]


@router.post("/reminders/{rid}/{action}")
def close_reminder(rid: int, action: str, request: Request, user: User = Depends(require("visits.write")),
                   db: DbSession = Depends(get_db, scope="function")):
    if action not in ("done", "dismiss"):
        raise AppError("إجراء غير معروف", 404, "not_found")
    r = db.get(MaintenanceReminder, rid)
    if not r:
        raise AppError("التذكير غير موجود", 404, "not_found")
    if r.status != "open":
        raise AppError("التذكير مغلق بالفعل", 409, "already_closed")
    r.status = "done" if action == "done" else "dismissed"
    r.completed_at = datetime.now(timezone.utc)
    audit(db, user, f"reminder.{r.status}", "reminder", r.id, ip=client_ip(request))
    return r_out(db, r)
