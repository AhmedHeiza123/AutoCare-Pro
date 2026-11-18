from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.core.audit import audit, snapshot
from app.core.errors import AppError
from app.core.text import compact, normalize
from app.db import get_db
from app.models import (Customer, Invoice, JobStatusHistory, Vehicle, VehicleOwnership, VehiclePlateHistory,
                        VehicleVisit)
from app.models.auth import User

router = APIRouter(prefix="/api", tags=["vehicles"])

VFIELDS = ["make", "model", "model_year", "trim", "vin", "plate", "engine_number", "engine_type",
           "fuel_type", "engine_capacity", "transmission", "color", "current_mileage",
           "registration_country", "notes", "is_active", "current_customer_id"]


class VehicleIn(BaseModel):
    customer_id: UUID | None = None
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    model_year: int | None = Field(None, ge=1900, le=2100)
    trim: str | None = None
    vin: str | None = Field(None, max_length=32)
    plate: str | None = Field(None, max_length=32)
    engine_number: str | None = None
    engine_type: str | None = None
    fuel_type: str | None = None
    engine_capacity: str | None = None
    transmission: str | None = None
    color: str | None = None
    current_mileage: int | None = Field(None, ge=0)
    registration_country: str | None = None
    notes: str | None = None


class VehiclePatch(BaseModel):
    make: str | None = None
    model: str | None = None
    model_year: int | None = Field(None, ge=1900, le=2100)
    trim: str | None = None
    vin: str | None = Field(None, max_length=32)
    plate: str | None = Field(None, max_length=32)
    engine_number: str | None = None
    engine_type: str | None = None
    fuel_type: str | None = None
    engine_capacity: str | None = None
    transmission: str | None = None
    color: str | None = None
    current_mileage: int | None = Field(None, ge=0)
    registration_country: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class OwnerChange(BaseModel):
    new_customer_id: UUID
    reason: str | None = None


def vout(v: Vehicle) -> dict:
    d = {f: getattr(v, f) for f in VFIELDS}
    d.update(id=str(v.id), vehicle_no=v.vehicle_no, current_customer_id=str(v.current_customer_id) if v.current_customer_id else None,
             created_at=v.created_at)
    return d


def _clean_vin(vin: str | None) -> str | None:
    vin = (vin or "").strip().upper().replace(" ", "")
    return vin or None


def _reindex(v: Vehicle) -> None:
    v.plate_compact = compact(v.plate) or None
    v.search_text = normalize(" ".join(filter(None, [
        v.make, v.model, str(v.model_year or ""), v.plate, v.vin, str(v.vehicle_no or "")])))


def _check_vin_free(db: DbSession, vin: str | None, exclude: UUID | None = None) -> None:
    if not vin:
        return
    q = select(Vehicle.id).where(Vehicle.vin == vin)
    if exclude:
        q = q.where(Vehicle.id != exclude)
    if db.scalar(q):
        raise AppError("رقم الشاسيه مسجل لسيارة أخرى", 409, "duplicate_vin")


def _set_plate(db: DbSession, v: Vehicle, plate: str | None, now: datetime) -> None:
    """Close the open plate-history row (if the plate changed) and open a new one."""
    if compact(plate) == (v.plate_compact or ""):
        return
    open_row = db.scalar(select(VehiclePlateHistory).where(
        VehiclePlateHistory.vehicle_id == v.id, VehiclePlateHistory.end_at.is_(None)))
    if open_row:
        open_row.end_at = now
    v.plate = plate or None
    if plate:
        db.add(VehiclePlateHistory(vehicle_id=v.id, plate=plate, plate_compact=compact(plate), start_at=now))


@router.post("/vehicles", status_code=201)
def create_vehicle(body: VehicleIn, request: Request, user: User = Depends(require("vehicles.write")),
                   db: DbSession = Depends(get_db, scope="function")):
    data = body.model_dump(exclude={"customer_id"})
    data["vin"] = _clean_vin(data["vin"])
    _check_vin_free(db, data["vin"])
    if body.customer_id and not db.get(Customer, body.customer_id):
        raise AppError("العميل غير موجود", 404, "customer_not_found")
    now = datetime.now(timezone.utc)
    plate = data.pop("plate")
    v = Vehicle(**data, current_customer_id=body.customer_id)
    db.add(v)
    db.flush()
    _set_plate(db, v, plate, now)
    if body.customer_id:
        db.add(VehicleOwnership(vehicle_id=v.id, customer_id=body.customer_id, start_at=now))
    db.flush()
    _reindex(v)
    audit(db, user, "vehicle.create", "vehicle", v.id, after=snapshot(v, VFIELDS), ip=client_ip(request))
    return vout(v)


@router.get("/vehicles")
def list_vehicles(q: str | None = None, customer_id: UUID | None = None, limit: int = Query(50, le=200),
                  offset: int = 0, _: User = Depends(require("vehicles.read")),
                  db: DbSession = Depends(get_db, scope="function")):
    stmt = select(Vehicle)
    if q:
        conds = [Vehicle.search_text.contains(normalize(q))]
        if compact(q):
            conds.append(Vehicle.plate_compact.contains(compact(q)))
        stmt = stmt.where(or_(*conds))
    if customer_id:
        stmt = stmt.where(Vehicle.current_customer_id == customer_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Vehicle.created_at.desc()).limit(limit).offset(offset))
    return {"total": total, "items": [vout(v) for v in rows]}


def _get_vehicle(db: DbSession, vehicle_id: UUID) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise AppError("السيارة غير موجودة", 404, "not_found")
    return v


@router.get("/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: UUID, _: User = Depends(require("vehicles.read")), db: DbSession = Depends(get_db, scope="function")):
    """Digital vehicle passport: identity + ownership and plate history."""
    v = _get_vehicle(db, vehicle_id)
    owners = db.execute(select(VehicleOwnership, Customer).join(Customer, Customer.id == VehicleOwnership.customer_id)
                        .where(VehicleOwnership.vehicle_id == v.id).order_by(VehicleOwnership.start_at)).all()
    plates = db.scalars(select(VehiclePlateHistory).where(VehiclePlateHistory.vehicle_id == v.id)
                        .order_by(VehiclePlateHistory.start_at))
    d = vout(v)
    d["ownership_history"] = [{"customer_id": str(c.id), "customer_name": c.full_name,
                               "start_at": o.start_at, "end_at": o.end_at} for o, c in owners]
    d["plate_history"] = [{"plate": p.plate, "start_at": p.start_at, "end_at": p.end_at} for p in plates]
    d["visit_count"] = db.scalar(select(func.count()).select_from(VehicleVisit).where(VehicleVisit.vehicle_id == v.id))
    return d


@router.patch("/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: UUID, body: VehiclePatch, request: Request,
                   user: User = Depends(require("vehicles.write")), db: DbSession = Depends(get_db, scope="function")):
    v = _get_vehicle(db, vehicle_id)
    before = snapshot(v, VFIELDS)
    changes = body.model_dump(exclude_unset=True)
    if "vin" in changes:
        changes["vin"] = _clean_vin(changes["vin"])
        _check_vin_free(db, changes["vin"], v.id)
    if "plate" in changes:
        _set_plate(db, v, changes.pop("plate"), datetime.now(timezone.utc))
    for k, val in changes.items():
        setattr(v, k, val)
    _reindex(v)
    audit(db, user, "vehicle.update", "vehicle", v.id, before=before, after=snapshot(v, VFIELDS),
          ip=client_ip(request))
    return vout(v)


@router.post("/vehicles/{vehicle_id}/change-owner")
def change_owner(vehicle_id: UUID, body: OwnerChange, request: Request,
                 user: User = Depends(require("vehicles.write")), db: DbSession = Depends(get_db, scope="function")):
    """Closes the open ownership and opens a new one; past visits keep their original customer."""
    v = _get_vehicle(db, vehicle_id)
    if not db.get(Customer, body.new_customer_id):
        raise AppError("العميل غير موجود", 404, "customer_not_found")
    if v.current_customer_id == body.new_customer_id:
        raise AppError("هذا العميل هو المالك الحالي", 409, "same_owner")
    now = datetime.now(timezone.utc)
    old = v.current_customer_id
    open_row = db.scalar(select(VehicleOwnership).where(
        VehicleOwnership.vehicle_id == v.id, VehicleOwnership.end_at.is_(None)))
    if open_row:
        open_row.end_at = now
        db.flush()
    db.add(VehicleOwnership(vehicle_id=v.id, customer_id=body.new_customer_id, start_at=now))
    v.current_customer_id = body.new_customer_id
    audit(db, user, "vehicle.change_owner", "vehicle", v.id,
          before={"customer_id": str(old) if old else None},
          after={"customer_id": str(body.new_customer_id)}, reason=body.reason, ip=client_ip(request))
    return vout(v)


# ---- visits / service history ---------------------------------------------
class VisitIn(BaseModel):
    vehicle_id: UUID
    arrival_at: datetime | None = None
    mileage: int | None = Field(None, ge=0)
    category: str | None = None
    complaint: str | None = None
    notes: str | None = None


class VisitPatch(BaseModel):
    mileage: int | None = Field(None, ge=0)
    category: str | None = None
    complaint: str | None = None
    diagnosis: str | None = None
    actual_repairs: str | None = None
    notes: str | None = None
    expected_completion_at: datetime | None = None
    expected_version: int | None = None
    reason: str | None = None  # mandatory when correcting a delivered visit


VISIT_FIELDS = ["vehicle_id", "customer_id", "plate_at_visit", "arrival_at", "mileage", "category",
                "complaint", "diagnosis", "actual_repairs", "status", "total_cost", "delivered_at", "notes",
                "expected_completion_at", "completed_at", "version"]


def visit_out(s: VehicleVisit) -> dict:
    d = {f: getattr(s, f) for f in VISIT_FIELDS}
    d.update(id=str(s.id), visit_no=s.visit_no, vehicle_id=str(s.vehicle_id), customer_id=str(s.customer_id),
             total_cost=str(s.total_cost))
    return d


@router.post("/visits", status_code=201)
def create_visit(body: VisitIn, request: Request, user: User = Depends(require("visits.write")),
                 db: DbSession = Depends(get_db, scope="function")):
    v = _get_vehicle(db, body.vehicle_id)
    if not v.current_customer_id:
        raise AppError("السيارة غير مرتبطة بعميل", 409, "no_owner")
    s = VehicleVisit(vehicle_id=v.id, customer_id=v.current_customer_id, plate_at_visit=v.plate,
                     mileage=body.mileage, category=body.category, complaint=body.complaint,
                     notes=body.notes, created_by=user.id)
    if body.arrival_at:
        s.arrival_at = body.arrival_at
    db.add(s)
    if body.mileage is not None and (v.current_mileage or 0) < body.mileage:
        v.current_mileage = body.mileage
    db.flush()
    db.add(JobStatusHistory(visit_id=s.id, to_status="received", changed_by=user.id))
    db.refresh(s)
    audit(db, user, "visit.create", "visit", s.id, after=snapshot(s, VISIT_FIELDS), ip=client_ip(request))
    return visit_out(s)


@router.get("/visits/{visit_id}")
def get_visit(visit_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    s = db.get(VehicleVisit, visit_id)
    if not s:
        raise AppError("الزيارة غير موجودة", 404, "not_found")
    return visit_out(s)


@router.patch("/visits/{visit_id}")
def update_visit(visit_id: UUID, body: VisitPatch, request: Request,
                 user: User = Depends(require("visits.write")), db: DbSession = Depends(get_db, scope="function")):
    s = db.get(VehicleVisit, visit_id)
    if not s:
        raise AppError("الزيارة غير موجودة", 404, "not_found")
    changes = body.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None)
    expected = changes.pop("expected_version", None)
    if expected is not None and s.version != expected:
        raise AppError("تم تعديل السجل من مستخدم آخر، أعد تحميل الصفحة", 409, "stale")
    if s.status == "delivered" and not reason:
        raise AppError("تعديل زيارة مسلمة يتطلب سبباً", 422, "reason_required")
    before = snapshot(s, VISIT_FIELDS)
    for k, val in changes.items():
        setattr(s, k, val)
    audit(db, user, "visit.update", "visit", s.id, before=before, after=snapshot(s, VISIT_FIELDS),
          reason=reason, ip=client_ip(request))
    return visit_out(s)


@router.get("/vehicles/{vehicle_id}/history")
def vehicle_history(vehicle_id: UUID, date_from: datetime | None = None, date_to: datetime | None = None,
                    mileage_min: int | None = None, mileage_max: int | None = None,
                    category: str | None = None, status: str | None = None,
                    limit: int = Query(100, le=500), offset: int = 0,
                    _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    """Chronological service timeline (newest first) with filters."""
    _get_vehicle(db, vehicle_id)
    stmt = select(VehicleVisit, Customer.full_name).join(Customer, Customer.id == VehicleVisit.customer_id) \
        .where(VehicleVisit.vehicle_id == vehicle_id)
    if date_from:
        stmt = stmt.where(VehicleVisit.arrival_at >= date_from)
    if date_to:
        stmt = stmt.where(VehicleVisit.arrival_at <= date_to)
    if mileage_min is not None:
        stmt = stmt.where(VehicleVisit.mileage >= mileage_min)
    if mileage_max is not None:
        stmt = stmt.where(VehicleVisit.mileage <= mileage_max)
    if category:
        stmt = stmt.where(VehicleVisit.category == category)
    if status:
        stmt = stmt.where(VehicleVisit.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(VehicleVisit.arrival_at.desc()).limit(limit).offset(offset)).all()
    # One batch for this page: no invoice query per history entry and no financial amounts exposed.
    invoice_states = {}
    priority = {"cancelled": 1, "draft": 2, "issued": 3}
    if rows:
        for visit_id, invoice_status in db.execute(select(Invoice.visit_id, Invoice.status).where(Invoice.visit_id.in_([s.id for s, _ in rows]))):
            if priority.get(invoice_status, 0) > priority.get(invoice_states.get(visit_id), 0):
                invoice_states[visit_id] = invoice_status
    return {"total": total, "items": [{**visit_out(s), "customer_name": name,
            "invoice_status": invoice_states.get(s.id, "not_invoiced")} for s, name in rows]}
