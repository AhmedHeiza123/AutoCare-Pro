from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.core.errors import AppError
from app.core.security import token_digest
from app.db import get_db
from app.models.auth import Session, User

COOKIE_NAME = "ac_session"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def current_user(request: Request, db: DbSession = Depends(get_db, scope="function")) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise AppError("يجب تسجيل الدخول", 401, "unauthenticated")
    sess = db.get(Session, token_digest(token))
    if not sess or sess.expires_at <= datetime.now(timezone.utc):
        raise AppError("انتهت الجلسة، سجل الدخول من جديد", 401, "session_expired")
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        raise AppError("الحساب غير مفعل", 401, "inactive")
    if request.method in UNSAFE and request.headers.get("X-CSRF-Token") != sess.csrf_token:
        raise AppError("طلب غير صالح (CSRF)", 403, "csrf")
    request.state.user = user
    return user


def require(permission: str):
    """Backend-enforced permission check; deny by default."""
    def dep(user: User = Depends(current_user)) -> User:
        if permission not in user.permissions:
            raise AppError("ليس لديك صلاحية لهذا الإجراء", 403, "forbidden")
        return user
    return dep


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
