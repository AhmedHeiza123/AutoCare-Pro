"""Job cards: reception, status workflow, operations, technicians, inspections, workshop board."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.api.vehicles import visit_out
from app.core.audit import audit, snapshot
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (Customer, Inspection, InspectionItem, Invoice, InvoiceItem, JobStatusHistory, ReceptionRecord,
                        RepairOperation, Technician, TechnicianAssignment, Vehicle, VehicleVisit)
from app.models.auth import User
from app.services import settings as cfg
from app.services.job_status import INSPECTION_STAGES, sync_work_status, transition_status
from app.services.pricing import parts_selling_total
from app.services.work_approval import require_work_approval
from app.services.templates import (CLOSED, CONDITION_POINTS, DASHBOARD_LIGHTS, FUEL_LEVELS, INSPECTION_TEMPLATES,
                                    REPAIR_TEMPLATES, STATUSES)

router = APIRouter(prefix="/api", tags=["jobs"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_job(db: DbSession, job_id: UUID, *, lock: bool = False) -> VehicleVisit:
    # NO KEY UPDATE serializes job changes while allowing payment/part foreign-key checks.
    job = db.get(VehicleVisit, job_id, with_for_update={"key_share": True} if lock else None, populate_existing=lock)
    if not job:
        raise AppError("أمر الصيانة غير موجود", 404, "not_found")
    return job


def require_open(job: VehicleVisit) -> None:
    if job.status in CLOSED:
        raise AppError("أمر الصيانة مغلق، أعد فتحه بصلاحية المدير أولاً", 409, "job_closed")


def check_version(job: VehicleVisit, expected: int | None) -> None:
    if expected is not None and job.version != expected:
        raise AppError("تم تعديل السجل من مستخدم آخر، أعد تحميل الصفحة", 409, "stale")


def add_history(db: DbSession, job: VehicleVisit, to: str, user: User | None, reason: str | None = None,
                frm: str | None = None) -> None:
    db.add(JobStatusHistory(visit_id=job.id, from_status=frm, to_status=to,
                            changed_by=user.id if user else None, reason=reason))


# ---- templates -------------------------------------------------------------
@router.get("/templates")
def templates(_: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    settings = cfg.get_section(db, "repair_catalog")
    catalog = [item for item in settings["items"] if item["active"]]
    custom = settings["custom_categories"]
    repairs = {category: [] for category in (*REPAIR_TEMPLATES, *(item["key"] for item in custom))}
    for item in catalog:
        if item["category"] in repairs:
            repairs[item["category"]].append(item["name"])
    return {"repairs": repairs, "repair_catalog": catalog, "repair_categories": custom, "inspections": INSPECTION_TEMPLATES,
            "condition_points": CONDITION_POINTS, "dashboard_lights": DASHBOARD_LIGHTS, "fuel_levels": FUEL_LEVELS, "statuses": STATUSES}


# ---- technicians -----------------------------------------------------------
class TechIn(BaseModel):
    employee_no: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    phone: str | None = None
    specialization: str | None = None
    notes: str | None = None


class TechPatch(BaseModel):
    name: str | None = None
    phone: str | None = None
    specialization: str | None = None
    notes: str | None = None
    is_active: bool | None = None


def tech_out(t: Technician) -> dict:
    return {"id": t.id, "employee_no": t.employee_no, "name": t.name, "phone": t.phone,
            "specialization": t.specialization, "is_active": t.is_active, "notes": t.notes}


@router.get("/technicians")
def list_technicians(active: bool | None = None, _: User = Depends(require("visits.read")),
                     db: DbSession = Depends(get_db, scope="function")):
    q = select(Technician).order_by(Technician.name)
    if active is not None:
        q = q.where(Technician.is_active == active)
    return [tech_out(t) for t in db.scalars(q)]


@router.post("/technicians", status_code=201)
def create_technician(body: TechIn, request: Request, user: User = Depends(require("technicians.manage")),
                      db: DbSession = Depends(get_db, scope="function")):
    if db.scalar(select(Technician.id).where(Technician.employee_no == body.employee_no)):
        raise AppError("رقم الموظف مستخدم من قبل", 409, "duplicate_employee_no")
    t = Technician(**body.model_dump())
    db.add(t)
    db.flush()
    audit(db, user, "technician.create", "technician", t.id, after=tech_out(t), ip=client_ip(request))
    return tech_out(t)


@router.patch("/technicians/{tech_id}")
def update_technician(tech_id: int, body: TechPatch, request: Request,
                      user: User = Depends(require("technicians.manage")), db: DbSession = Depends(get_db, scope="function")):
    t = db.get(Technician, tech_id)
    if not t:
        raise AppError("الفني غير موجود", 404, "not_found")
    before = tech_out(t)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    audit(db, user, "technician.update", "technician", t.id, before=before, after=tech_out(t), ip=client_ip(request))
    return tech_out(t)


# ---- reception (check-in) ----------------------------------------------------
class Complaint(BaseModel):
    category: str | None = None
    text: str | None = None


class ConditionPoint(BaseModel):
    state: str = Field(pattern="^(ok|damaged|na)$")
    note: str | None = None
    kind: str | None = Field(default=None, pattern="^(dent|scratch|rust|crack|broken|other)$")


class ReceptionIn(BaseModel):
    vehicle_id: UUID
    mileage: int = Field(ge=0)
    fuel_level: str | None = None
    complaints: list[Complaint] = []
    condition: dict[str, ConditionPoint] = {}
    belongings: list[str] = []
    dashboard_lights: list[str] = []
    technician_id: int | None = None
    expected_completion_at: datetime | None = None
    notes: str | None = None


@router.post("/reception", status_code=201)
def receive_vehicle(body: ReceptionIn, request: Request, user: User = Depends(require("visits.write")),
                    db: DbSession = Depends(get_db, scope="function")):
    """Atomic check-in: creates the job card, reception record, first status entry and assignment."""
    v = db.get(Vehicle, body.vehicle_id)
    if not v:
        raise AppError("السيارة غير موجودة", 404, "not_found")
    if not v.current_customer_id:
        raise AppError("السيارة غير مرتبطة بعميل", 409, "no_owner")
    if body.fuel_level and body.fuel_level not in FUEL_LEVELS:
        raise AppError("مستوى البنزين غير صحيح", 422, "bad_fuel")
    bad = [k for k in body.condition if k not in CONDITION_POINTS]
    if bad:
        raise AppError("نقطة فحص غير معروفة", 422, "bad_condition_point")
    if any(x not in DASHBOARD_LIGHTS for x in body.dashboard_lights):
        raise AppError("لمبة تابلوه غير معروفة", 422, "bad_dashboard_light")
    active = db.scalar(select(VehicleVisit.id).where(VehicleVisit.vehicle_id == v.id,
                                                     VehicleVisit.status.notin_(CLOSED)))
    if active:  # prevent receiving the same car twice by accident
        raise AppError("العربية دي عندها أمر صيانة مفتوح بالفعل", 409, "already_open")
    tech = None
    if body.technician_id is not None:
        tech = db.get(Technician, body.technician_id)
        if not tech or not tech.is_active:
            raise AppError("الفني غير موجود أو غير مفعل", 422, "bad_technician")
    first = next((c for c in body.complaints if c.category), None)
    complaint_text = " | ".join(c.text for c in body.complaints if c.text) or None
    job = VehicleVisit(vehicle_id=v.id, customer_id=v.current_customer_id, plate_at_visit=v.plate,
                       mileage=body.mileage, category=first.category if first else None,
                       complaint=complaint_text, notes=body.notes, status="received", created_by=user.id,
                       expected_completion_at=body.expected_completion_at)
    db.add(job)
    if (v.current_mileage or 0) < body.mileage:
        v.current_mileage = body.mileage
    db.flush()
    db.add(ReceptionRecord(visit_id=job.id, fuel_level=body.fuel_level,
                           condition={k: p.model_dump() for k, p in body.condition.items()},
                           complaints=[c.model_dump() for c in body.complaints],
                           belongings=body.belongings, dashboard_lights=sorted(set(body.dashboard_lights)), notes=body.notes))
    add_history(db, job, "received", user)
    if tech:
        db.add(TechnicianAssignment(visit_id=job.id, technician_id=tech.id, assigned_by=user.id))
        transition_status(db, job, "inspection_pending", user, "تلقائي: تم تعيين فني للفحص", client_ip(request))
    db.flush()
    db.refresh(job)
    audit(db, user, "job.receive", "job", job.id, after=snapshot(job, ["vehicle_id", "customer_id", "mileage", "status"]),
          ip=client_ip(request))
    return visit_out(job)


@router.get("/jobs/{job_id}/receipt")
def reception_receipt(job_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    rec = db.get(ReceptionRecord, job.id)
    v = db.get(Vehicle, job.vehicle_id)
    c = db.get(Customer, job.customer_id)
    return {"job_no": job.visit_no, "arrival_at": job.arrival_at, "customer": {"name": c.full_name, "mobile": c.mobile},
            "vehicle": {"make": v.make, "model": v.model, "plate": job.plate_at_visit, "year": v.model_year},
            "mileage": job.mileage, "fuel_level": rec.fuel_level if rec else None,
            "complaints": rec.complaints if rec else [], "condition": rec.condition if rec else {},
            "belongings": rec.belongings if rec else [], "dashboard_lights": (rec.dashboard_lights if rec else None) or [],
            "notes": job.notes}


# ---- job card detail -----------------------------------------------------------
def op_out(o: RepairOperation) -> dict:
    return {"id": o.id, "category": o.category, "description": o.description, "technician_id": o.technician_id,
            "status": o.status, "started_at": o.started_at, "ended_at": o.ended_at,
            "labor_hours": f"{Decimal(o.labor_hours):.2f}", "labor_rate": f"{Decimal(o.labor_rate):.2f}",
            "labor_amount": f"{Decimal(o.labor_amount):.2f}", "notes": o.notes}


def job_full(db: DbSession, job: VehicleVisit) -> dict:
    d = visit_out(job)
    v = db.get(Vehicle, job.vehicle_id)
    c = db.get(Customer, job.customer_id)
    d["vehicle"] = {"id": str(v.id), "make": v.make, "model": v.model, "plate": v.plate, "model_year": v.model_year}
    d["customer"] = {"id": str(c.id), "name": c.full_name, "mobile": c.mobile}
    d["operations"] = [op_out(o) for o in db.scalars(
        select(RepairOperation).where(RepairOperation.visit_id == job.id).order_by(RepairOperation.id))]
    d["technicians"] = [tech_out(t) for t in db.scalars(
        select(Technician).join(TechnicianAssignment, TechnicianAssignment.technician_id == Technician.id)
        .where(TechnicianAssignment.visit_id == job.id).order_by(Technician.name))]
    d["status_history"] = [
        {"from": h.from_status, "to": h.to_status, "at": h.changed_at, "reason": h.reason, "by": uname}
        for h, uname in db.execute(select(JobStatusHistory, User.username)
                                   .outerjoin(User, User.id == JobStatusHistory.changed_by)
                                   .where(JobStatusHistory.visit_id == job.id).order_by(JobStatusHistory.id))]
    d["inspections"] = []
    inspections = list(db.scalars(select(Inspection).where(Inspection.visit_id == job.id).order_by(Inspection.id)))
    items_by_inspection: dict[int, list[InspectionItem]] = {}
    if inspections:
        for item in db.scalars(select(InspectionItem).where(
                InspectionItem.inspection_id.in_([i.id for i in inspections])).order_by(InspectionItem.id)):
            items_by_inspection.setdefault(item.inspection_id, []).append(item)
    for i in inspections:
        items = items_by_inspection.get(i.id, [])
        d["inspections"].append({"id": i.id, "category": i.category, "notes": i.notes, "created_at": i.created_at,
                                 "items": [{"name": x.name, "status": x.status, "note": x.note,
                                            "recommendation": x.recommendation,
                                            "estimate": str(x.estimate) if x.estimate is not None else None}
                                           for x in items]})
    rec = db.get(ReceptionRecord, job.id)
    d["reception"] = ({"fuel_level": rec.fuel_level, "condition": rec.condition, "complaints": rec.complaints,
                       "belongings": rec.belongings, "dashboard_lights": rec.dashboard_lights or []} if rec else None)
    return d


@router.get("/jobs/{job_id}")
def get_job_full(job_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    return job_full(db, get_job(db, job_id))


# ---- status workflow -------------------------------------------------------------
class StatusIn(BaseModel):
    status: str
    reason: str | None = None
    expected_version: int | None = None


@router.post("/jobs/{job_id}/status")
def change_status(job_id: UUID, body: StatusIn, request: Request, user: User = Depends(require("visits.write")),
                  db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id, lock=True)
    check_version(job, body.expected_version)
    to, frm = body.status, job.status
    if to not in STATUSES:
        raise AppError("حالة غير معروفة", 422, "bad_status")
    if to == frm:
        raise AppError("الأمر بالفعل في هذه الحالة", 409, "same_status")
    if to == "delivered":  # delivery has its own audited, payment-gated workflow
        raise AppError("استخدم شاشة التسليم لتسليم العربية", 422, "use_delivery")
    if to == "ready":
        raise AppError("استخدم فحص الجودة لاعتماد جاهزية العربية", 422, "use_quality_check")
    reason = (body.reason or "").strip() or None
    can_override = "jobs.override" in user.permissions
    if frm in CLOSED:  # reopening a closed job
        if not can_override:
            raise AppError("إعادة فتح أمر مغلق تحتاج صلاحية المدير", 403, "forbidden")
        if not reason:
            raise AppError("اكتب سبب إعادة الفتح", 422, "reason_required")
    if to == "cancelled" and not reason:
        raise AppError("اكتب سبب الإلغاء", 422, "reason_required")
    if to == "delivered" and frm != "ready":  # no accidental delivery of unfinished jobs
        if not can_override:
            raise AppError("لا يمكن تسليم عربية غير جاهزة", 409, "not_ready")
        if not reason:
            raise AppError("تسليم عربية غير جاهزة يحتاج سبباً", 422, "reason_required")
    job.status = to
    now = _now()
    if to == "delivered":
        job.delivered_at = now
    if to in ("ready", "delivered") and not job.completed_at:
        job.completed_at = now
    if to not in ("ready", "delivered"):
        job.completed_at = None
    if frm in CLOSED:
        job.delivered_at = None if to != "delivered" else job.delivered_at
        job.completed_at = None if to not in ("ready", "delivered") else job.completed_at
    add_history(db, job, to, user, reason, frm)
    audit(db, user, "job.status", "job", job.id, before={"status": frm}, after={"status": to}, reason=reason,
          ip=client_ip(request))
    db.flush()
    db.refresh(job)
    return visit_out(job)


# ---- technician assignment --------------------------------------------------------
class AssignIn(BaseModel):
    technician_id: int


@router.post("/jobs/{job_id}/assign")
def assign(job_id: UUID, body: AssignIn, request: Request, user: User = Depends(require("visits.write")),
           db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    require_open(job)
    t = db.get(Technician, body.technician_id)
    if not t or not t.is_active:
        raise AppError("الفني غير موجود أو غير مفعل", 422, "bad_technician")
    if db.scalar(select(TechnicianAssignment.id).where(TechnicianAssignment.visit_id == job.id,
                                                       TechnicianAssignment.technician_id == t.id)):
        raise AppError("الفني معين بالفعل", 409, "already_assigned")
    db.add(TechnicianAssignment(visit_id=job.id, technician_id=t.id, assigned_by=user.id))
    if job.status == "received":
        transition_status(db, job, "inspection_pending", user, "تلقائي: تم تعيين فني للفحص", client_ip(request))
    audit(db, user, "job.assign", "job", job.id, after={"technician_id": t.id}, ip=client_ip(request))
    db.flush()
    return job_full(db, job)


@router.post("/jobs/{job_id}/unassign")
def unassign(job_id: UUID, body: AssignIn, request: Request, user: User = Depends(require("visits.write")),
             db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    require_open(job)
    row = db.scalar(select(TechnicianAssignment).where(TechnicianAssignment.visit_id == job.id,
                                                       TechnicianAssignment.technician_id == body.technician_id))
    if not row:
        raise AppError("الفني غير معين على هذا الأمر", 404, "not_found")
    db.delete(row)
    audit(db, user, "job.unassign", "job", job.id, before={"technician_id": body.technician_id}, ip=client_ip(request))
    db.flush()
    return job_full(db, job)


# ---- repair operations -------------------------------------------------------------
OP_STATUSES = ("pending", "in_progress", "done", "cancelled")


class OpIn(BaseModel):
    category: str | None = None
    description: str = Field(min_length=2)
    technician_id: int | None = None
    labor_hours: Decimal = Field(Decimal("0"), ge=0, max_digits=8, decimal_places=2)
    labor_rate: Decimal = Field(Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None


class OpPatch(BaseModel):
    description: str | None = Field(None, min_length=2)
    technician_id: int | None = None
    status: str | None = None
    labor_hours: Decimal | None = Field(None, ge=0, max_digits=8, decimal_places=2)
    labor_rate: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None


def recompute_total(db: DbSession, job: VehicleVisit) -> None:
    """Job total = non-cancelled operation labor + selling price of non-cancelled parts (net of returns)."""
    db.flush()
    labor = db.scalar(select(func.coalesce(func.sum(RepairOperation.labor_amount), 0))
                      .where(RepairOperation.visit_id == job.id, RepairOperation.status != "cancelled"))
    job.total_cost = to_money(labor) + parts_selling_total(db, job.id)


def _check_tech(db: DbSession, tech_id: int | None) -> None:
    if tech_id is not None:
        t = db.get(Technician, tech_id)
        if not t or not t.is_active:
            raise AppError("الفني غير موجود أو غير مفعل", 422, "bad_technician")


@router.post("/jobs/{job_id}/operations", status_code=201)
def add_operation(job_id: UUID, body: OpIn, request: Request, user: User = Depends(require("visits.write")),
                  db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id, lock=True)
    require_open(job)
    _check_tech(db, body.technician_id)
    data = body.model_dump()
    if "labor_rate" not in body.model_fields_set:  # default hourly rate from the settings
        data["labor_rate"] = Decimal(cfg.get_section(db, "finance")["default_labor_rate"])
    op = RepairOperation(visit_id=job.id, **data, labor_amount=to_money(body.labor_hours * data["labor_rate"]))
    db.add(op)
    recompute_total(db, job)
    sync_work_status(db, job, user, "تلقائي: تمت إضافة عملية إصلاح", client_ip(request))
    audit(db, user, "operation.create", "operation", op.id, after=op_out(op), ip=client_ip(request))
    return op_out(op)


@router.patch("/operations/{op_id}")
def update_operation(op_id: int, body: OpPatch, request: Request, user: User = Depends(require("visits.write")),
                     db: DbSession = Depends(get_db, scope="function")):
    op = db.get(RepairOperation, op_id)
    if not op:
        raise AppError("العملية غير موجودة", 404, "not_found")
    job = get_job(db, op.visit_id, lock=True)
    require_open(job)
    db.refresh(op)
    before = op_out(op)
    ch = body.model_dump(exclude_unset=True)
    if "technician_id" in ch:
        _check_tech(db, ch["technician_id"])
    st = ch.pop("status", None)
    money_change = bool({"description", "labor_hours", "labor_rate"} & ch.keys()) or st == "cancelled"
    if money_change and db.scalar(select(func.count()).select_from(InvoiceItem).join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                                  .where(InvoiceItem.operation_id == op.id, Invoice.status == "issued")):
        raise AppError("العملية مدرجة في فاتورة صادرة ولا يمكن تعديلها أو حذفها — ألغِ الفاتورة أولاً أو أصدر إشعاراً دائناً", 409, "operation_invoiced")
    for k, v in ch.items():
        setattr(op, k, v)
    if st in ("in_progress", "done") or (money_change and st != "cancelled" and op.status in ("in_progress", "done")):
        require_work_approval(db, job.id, operation_id=op.id,
                              amount=to_money(Decimal(op.labor_hours) * Decimal(op.labor_rate)))
    if st:
        if st not in OP_STATUSES:
            raise AppError("حالة العملية غير صحيحة", 422, "bad_status")
        now = _now()
        if st == "in_progress" and not op.started_at:
            op.started_at = now
        if st == "done":
            op.started_at = op.started_at or now
            op.ended_at = now
        op.status = st
    op.labor_amount = to_money(Decimal(op.labor_hours) * Decimal(op.labor_rate))
    recompute_total(db, job)
    if st and st != before["status"]:
        sync_work_status(db, job, user, "تلقائي: تم تحديث تقدم الإصلاح", client_ip(request))
    audit(db, user, "operation.update", "operation", op.id, before=before, after=op_out(op), ip=client_ip(request))
    return op_out(op)


# ---- inspections -----------------------------------------------------------------------
class InspItem(BaseModel):
    name: str = Field(min_length=1)
    status: str = Field(pattern="^(good|attention|critical|na)$")
    note: str | None = None
    recommendation: str | None = None
    estimate: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)


class InspIn(BaseModel):
    category: str
    items: list[InspItem] = Field(min_length=1)
    notes: str | None = None


@router.post("/jobs/{job_id}/inspections", status_code=201)
def add_inspection(job_id: UUID, body: InspIn, request: Request, user: User = Depends(require("visits.write")),
                   db: DbSession = Depends(get_db, scope="function")):
    job = get_job(db, job_id)
    require_open(job)
    if body.category not in INSPECTION_TEMPLATES:
        raise AppError("نوع الفحص غير معروف", 422, "bad_category")
    insp = Inspection(visit_id=job.id, category=body.category, notes=body.notes, created_by=user.id)
    db.add(insp)
    db.flush()
    for it in body.items:
        db.add(InspectionItem(inspection_id=insp.id, **it.model_dump()))
    db.flush()
    if job.status in INSPECTION_STAGES:
        transition_status(db, job, "under_inspection", user, "تلقائي: تم تسجيل نتائج الفحص", client_ip(request))
    audit(db, user, "inspection.create", "inspection", insp.id,
          after={"category": body.category, "items": len(body.items),
                 "critical": sum(1 for i in body.items if i.status == "critical")}, ip=client_ip(request))
    return {"id": insp.id}


# ---- workshop board ----------------------------------------------------------------------
@router.get("/board")
def board(_: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    now = _now()
    rows = db.execute(
        select(VehicleVisit, Vehicle, Customer.full_name)
        .join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id)
        .join(Customer, Customer.id == VehicleVisit.customer_id)
        .where(VehicleVisit.status.notin_(CLOSED)).order_by(VehicleVisit.arrival_at)).all()
    techs: dict = {}
    if rows:
        ids = [r[0].id for r in rows]
        for vid, name in db.execute(select(TechnicianAssignment.visit_id, Technician.name)
                                    .join(Technician, Technician.id == TechnicianAssignment.technician_id)
                                    .where(TechnicianAssignment.visit_id.in_(ids)).order_by(Technician.name)):
            techs.setdefault(vid, []).append(name)
    return [{"id": str(j.id), "job_no": j.visit_no, "status": j.status, "plate": v.plate, "make": v.make,
             "model": v.model, "customer": cname, "technicians": techs.get(j.id, []),
             "arrival_at": j.arrival_at, "days_in_workshop": (now - j.arrival_at).days,
             "expected_completion_at": j.expected_completion_at,
             "delayed": bool(j.expected_completion_at and j.expected_completion_at < now)}
            for j, v, cname in rows]
