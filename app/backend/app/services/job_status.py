"""Event-driven job progress; manual choices persist until the next work event."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.models import JobStatusHistory, PartPurchase, RepairOperation, VehicleVisit
from app.models.auth import User
from app.services.templates import CLOSED

INSPECTION_STAGES = ("received", "inspection_pending", "under_inspection")
QUOTATION_STAGES = (*INSPECTION_STAGES, "waiting_quotation")


def transition_status(db: Session, job: VehicleVisit, target: str, user: User,
                      reason: str, ip: str | None = None) -> None:
    """Change only open jobs, recording actor/reason in the same transaction."""
    if job.status in CLOSED:
        return
    job.completed_at = None
    if job.status == target:
        return
    previous = job.status
    job.status = target
    db.add(JobStatusHistory(visit_id=job.id, from_status=previous, to_status=target,
                            changed_by=user.id, reason=reason))
    audit(db, user, "job.status.auto", "job", job.id, before={"status": previous},
          after={"status": target}, reason=reason, ip=ip)


def sync_work_status(db: Session, job: VehicleVisit, user: User, reason: str,
                     ip: str | None = None) -> None:
    """Run only after work changes, never for reads or price/note edits.

    Approval takes precedence; missing parts block work completion. An empty
    job is not finished work. Quality approval remains an explicit action.
    """
    if job.status in CLOSED:
        return
    # Claim the parent version even when this event leaves its status unchanged.
    # Concurrent work edits must retry rather than both miss the last completion.
    job.version += 1
    db.flush()
    if job.status == "waiting_approval":
        return
    operations = list(db.scalars(select(RepairOperation.status).where(
        RepairOperation.visit_id == job.id, RepairOperation.status != "cancelled")))
    parts = list(db.scalars(select(PartPurchase.status).where(
        PartPurchase.visit_id == job.id, PartPurchase.status.notin_(("cancelled", "returned")))))
    if any(s in ("requested", "ordered", "purchased") for s in parts):
        target = "waiting_parts"
    elif (operations or parts) and all(s == "done" for s in operations) and all(s == "installed" for s in parts):
        target = "quality_check"
    elif (any(s in ("in_progress", "done") for s in operations) or "installed" in parts
          or job.status in ("waiting_parts", "in_progress", "quality_check", "ready")):
        target = "in_progress"
    else:
        return
    transition_status(db, job, target, user, reason, ip)
