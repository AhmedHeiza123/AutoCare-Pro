"""Read-only access to the audit trail (sensitive: permission audit.read)."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import require
from app.db import get_db
from app.models import AuditLog
from app.models.auth import User

router = APIRouter(prefix="/api", tags=["audit"])
TZ = ZoneInfo("Asia/Qatar")


@router.get("/audit")
def audit_log(action: str | None = None, entity_type: str | None = None, entity_id: str | None = None,
              username: str | None = None, date_from: date | None = None, date_to: date | None = None,
              limit: int = Query(100, le=500), offset: int = 0, _: User = Depends(require("audit.read")),
              db: DbSession = Depends(get_db, scope="function")):
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action.like(f"{action}%"))
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    if username:
        q = q.where(AuditLog.username == username.lower())
    if date_from:
        q = q.where(AuditLog.ts >= datetime.combine(date_from, time.min, TZ))
    if date_to:
        q = q.where(AuditLog.ts < datetime.combine(date_to + timedelta(days=1), time.min, TZ))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(AuditLog.id.desc()).limit(limit).offset(offset))
    return {"total": total, "items": [{"id": r.id, "ts": r.ts, "username": r.username, "action": r.action,
                                       "entity_type": r.entity_type, "entity_id": r.entity_id, "before": r.before,
                                       "after": r.after, "reason": r.reason, "ip": r.ip} for r in rows]}
