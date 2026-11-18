"""A simple, explainable 'health' indicator for a vehicle, computed from what the workshop already knows."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import require
from app.api.warranty import reminder_state, warranty_status
from app.core.errors import AppError
from app.db import get_db
from app.models import Inspection, InspectionItem, MaintenanceReminder, Vehicle, VehicleVisit, Warranty
from app.models.auth import User

router = APIRouter(prefix="/api", tags=["vehicles"])

PENALTY = {"overdue": 30, "due_soon": 10, "critical": 25, "attention": 10}


def level_of(score: int) -> str:
    return "good" if score >= 80 else "fair" if score >= 50 else "poor"


@router.get("/vehicles/{vehicle_id}/health")
def vehicle_health(vehicle_id: UUID, _: User = Depends(require("visits.read")), db: DbSession = Depends(get_db, scope="function")):
    """Score 0-100 = 100 minus: 30 per overdue reminder, 10 per reminder due soon, and (from the latest inspected visit)
    25 per critical item and 10 per item needing attention. The reasons are returned so screens can explain the number."""
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise AppError("السيارة غير موجودة", 404, "not_found")
    states = [reminder_state(r, v.current_mileage) for r in db.scalars(
        select(MaintenanceReminder).where(MaintenanceReminder.vehicle_id == v.id, MaintenanceReminder.status == "open"))]
    overdue, due_soon = states.count("overdue"), states.count("due_soon")
    last = db.scalar(select(VehicleVisit).join(Inspection, Inspection.visit_id == VehicleVisit.id)
                     .where(VehicleVisit.vehicle_id == v.id).order_by(VehicleVisit.arrival_at.desc()).limit(1))
    critical = attention = 0
    if last:
        for status in db.scalars(select(InspectionItem.status).join(Inspection, Inspection.id == InspectionItem.inspection_id)
                                 .where(Inspection.visit_id == last.id)):
            critical += status == "critical"
            attention += status == "attention"
    score = max(0, 100 - PENALTY["overdue"] * overdue - PENALTY["due_soon"] * due_soon
                - PENALTY["critical"] * critical - PENALTY["attention"] * attention)
    active_w = sum(1 for w in db.scalars(select(Warranty).where(Warranty.vehicle_id == v.id)) if warranty_status(w) == "active")
    return {"score": score, "level": level_of(score), "overdue_reminders": overdue, "due_soon_reminders": due_soon,
            "critical_items": critical, "attention_items": attention, "active_warranties": active_w,
            "last_inspection_job": last.visit_no if last else None}
