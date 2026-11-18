from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.auth import AuditLog, User


def _jsonable(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (Decimal, UUID)):
        return str(v)
    return v


def _clean(d: dict | None) -> dict | None:
    return None if d is None else {k: _jsonable(v) for k, v in d.items()}


def snapshot(obj, fields: list[str]) -> dict:
    return {f: _jsonable(getattr(obj, f)) for f in fields}


def audit(db: Session, user: User | None, action: str, entity_type: str | None = None,
          entity_id=None, before: dict | None = None, after: dict | None = None,
          reason: str | None = None, ip: str | None = None, username: str | None = None) -> None:
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else username,
        action=action, entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=_clean(before), after=_clean(after), reason=reason, ip=ip,
    ))
