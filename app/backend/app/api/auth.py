from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import COOKIE_NAME, client_ip, current_user, require
from app.core.audit import audit
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (DUMMY_HASH, MIN_PASSWORD_LEN, ROLES, hash_password, login_limiter,
                               new_token, token_digest, verify_password)
from app.db import get_db
from app.services import settings as cfg
svc_settings = cfg
from app.models.auth import Role, RolePermission, Session, User, UserRole

router = APIRouter(prefix="/api", tags=["auth"])


def seed_roles(db: DbSession) -> None:
    """Idempotently create/refresh default roles and their permissions."""
    for name, (label, perms) in ROLES.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, label_ar=label)
            db.add(role)
            db.flush()
        have = {p.permission for p in role.permissions}
        for p in perms:
            if p not in have:
                db.add(RolePermission(role_id=role.id, permission=p))
    db.flush()


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.\-]+$")
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=MIN_PASSWORD_LEN, max_length=200)


class UserCreate(UserIn):
    role: str
    roles: list[str] | None = Field(None, max_length=10)  # optional: the primary role (above) plus additional ones


class SetupIn(UserIn):
    workshop: dict | None = None
    currency: str | None = Field(None, pattern=r"^[A-Za-z]{3}$")
    default_tax_rate: float | None = Field(None, ge=0, le=100)
    backup_dir: str | None = None
    language: str | None = Field(None, pattern="^(ar|en)$")


class LoginIn(BaseModel):
    username: str
    password: str


def user_out(u: User) -> dict:
    # "role" / "role_label" stay the PRIMARY role (existing clients); "roles" lists every role, primary first
    return {"id": str(u.id), "username": u.username, "full_name": u.full_name, "role": u.role.name,
            "role_label": u.role.label_ar, "roles": [{"name": r.name, "label": r.label_ar} for r in u.all_roles],
            "is_active": u.is_active, "permissions": sorted(u.permissions)}


def _resolve_roles(db: DbSession, names: list[str]) -> list[Role]:
    """Role rows for the given names (unique, order kept); an unknown name or an empty list is refused."""
    wanted = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))
    if not wanted:
        raise AppError("يجب اختيار دور واحد على الأقل", 422, "no_role")
    found = {r.name: r for r in db.scalars(select(Role).where(Role.name.in_(wanted)))}
    missing = [n for n in wanted if n not in found]
    if missing:
        raise AppError("الدور غير موجود", 422, "bad_role")
    return [found[n] for n in wanted]


def _apply_roles(db: DbSession, user: User, roles: list[Role]) -> bool:
    """Make `roles` the user's complete role set. The current primary role stays primary when it is kept; otherwise the first one becomes
    primary. Returns True when something changed."""
    ids = [r.id for r in roles]
    primary = user.role_id if user.role_id in ids else ids[0]
    extras = [i for i in ids if i != primary]
    before = {user.role_id, *[r.id for r in user.extra_roles]}
    if before == {primary, *extras}:
        return False
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    user.role_id = primary
    for i in extras:
        db.add(UserRole(user_id=user.id, role_id=i))
    db.flush()
    db.refresh(user)
    return True


@router.get("/auth/setup-needed")
def setup_needed(db: DbSession = Depends(get_db, scope="function")):
    return {"setup_needed": db.scalar(select(func.count()).select_from(User)) == 0,
            "default_language": svc_settings.get_section(db, "general")["language"]}


@router.post("/auth/setup", status_code=201)
def first_admin(body: SetupIn, request: Request, db: DbSession = Depends(get_db, scope="function")):
    """First-run wizard: creates the first administrator (and optionally workshop info, currency, tax, backup folder).
    Refuses once any user exists."""
    from app.api.settings_api import Finance, Workshop
    from app.backup import service as backup_service
    from app.models import AppSetting
    seed_roles(db)
    db.execute(select(func.pg_advisory_xact_lock(7001)))  # serialize concurrent setup calls
    if db.scalar(select(func.count()).select_from(User)) > 0:
        raise AppError("تم إعداد النظام من قبل", 409, "already_setup")
    # validate everything before writing anything
    try:
        workshop = Workshop.model_validate(body.workshop).model_dump(mode="json") if body.workshop else None
    except Exception as e:  # noqa: BLE001 - pydantic ValidationError
        raise AppError("بيانات الورشة غير صحيحة", 422, "bad_workshop") from e
    finance = None
    if body.currency or body.default_tax_rate is not None:
        finance = svc_settings.get_section(db, "finance")
        if body.currency:
            finance["currency"] = body.currency.upper()
        if body.default_tax_rate is not None:
            finance["default_tax_rate"] = str(body.default_tax_rate)
        finance = Finance.model_validate(finance).model_dump(mode="json")
    backup_dir = None
    if body.backup_dir and body.backup_dir.strip():
        from pathlib import Path
        p = Path(body.backup_dir.strip())
        try:
            p.mkdir(parents=True, exist_ok=True)
            (p / ".write-test").write_bytes(b"ok")
            (p / ".write-test").unlink()
        except OSError as e:
            raise AppError("لا يمكن الكتابة في مجلد النسخ الاحتياطي المحدد", 422, "bad_directory") from e
        backup_dir = str(p)
    role = db.scalar(select(Role).where(Role.name == "admin"))
    user = User(username=body.username.lower(), full_name=body.full_name,
                password_hash=hash_password(body.password), role_id=role.id)
    db.add(user)
    db.flush()
    if body.language:
        general = svc_settings.get_section(db, "general")
        general["language"] = body.language
        svc_settings.set_section(db, "general", general)
    if workshop:
        svc_settings.set_section(db, "workshop", workshop)
    if finance:
        svc_settings.set_section(db, "finance", finance)
    if backup_dir:
        cfg = backup_service.get_backup_settings(db)
        cfg["dir"] = backup_dir
        db.merge(AppSetting(key="backup", value=cfg))
    audit(db, user, "setup.first_admin", "user", user.id, after={"workshop": bool(workshop), "currency": body.currency,
                                                                "backup_dir": backup_dir}, ip=client_ip(request))
    return user_out(user)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: DbSession = Depends(get_db, scope="function")):
    s = get_settings()
    sec = cfg.get_section(db, "security")
    ip = client_ip(request)
    if not login_limiter.hit(ip or "unknown"):
        raise AppError("محاولات كثيرة، حاول لاحقاً", 429, "rate_limited")
    username = body.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    now = datetime.now(timezone.utc)
    if user and user.locked_until and user.locked_until > now:
        verify_password(DUMMY_HASH, body.password)
        raise AppError("الحساب مقفل مؤقتاً، حاول لاحقاً", 423, "locked")
    ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password) and user is not None
    if not ok or not user.is_active:
        if user:
            user.failed_attempts += 1
            if user.failed_attempts >= sec["max_failed_logins"]:
                user.locked_until = now + timedelta(minutes=sec["lockout_minutes"])
                user.failed_attempts = 0
        audit(db, user, "login.failed", "user", user.id if user else None, ip=ip, username=username)
        db.commit()  # persist the failure record/counter before returning the error
        raise AppError("اسم المستخدم أو كلمة المرور غير صحيحة", 401, "bad_credentials")
    user.failed_attempts, user.locked_until = 0, None
    db.execute(delete(Session).where(Session.expires_at < now))  # expired sessions are useless; purge them on each sign-in
    token, csrf = new_token(), new_token()
    db.add(Session(token_hash=token_digest(token), user_id=user.id, csrf_token=csrf,
                   expires_at=now + timedelta(minutes=sec["session_minutes"])))
    audit(db, user, "login.success", "user", user.id, ip=ip)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=s.cookie_secure,
                        max_age=sec["session_minutes"] * 60, path="/")
    return {"csrf_token": csrf, "user": user_out(user)}


@router.post("/auth/logout")
def logout(request: Request, response: Response, user: User = Depends(current_user),
           db: DbSession = Depends(get_db, scope="function")):
    sess = db.get(Session, token_digest(request.cookies[COOKIE_NAME]))
    if sess:
        db.delete(sess)
    audit(db, user, "logout", "user", user.id, ip=client_ip(request))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request, user: User = Depends(current_user), db: DbSession = Depends(get_db, scope="function")):
    sess = db.get(Session, token_digest(request.cookies[COOKIE_NAME]))
    return {"csrf_token": sess.csrf_token, "user": user_out(user)}


# ---- user administration ----------------------------------------------------
@router.get("/users")
def list_users(_: User = Depends(require("users.manage")), db: DbSession = Depends(get_db, scope="function")):
    return [user_out(u) for u in db.scalars(select(User).order_by(User.username))]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, request: Request, actor: User = Depends(require("users.manage")),
                db: DbSession = Depends(get_db, scope="function")):
    role = db.scalar(select(Role).where(Role.name == body.role))
    if not role:
        raise AppError("الدور غير موجود", 422, "bad_role")
    extra = [r for r in _resolve_roles(db, body.roles) if r.id != role.id] if body.roles else []
    if db.scalar(select(User).where(User.username == body.username.lower())):
        raise AppError("اسم المستخدم مستخدم من قبل", 409, "duplicate_username")
    user = User(username=body.username.lower(), full_name=body.full_name,
                password_hash=hash_password(body.password), role_id=role.id)
    db.add(user)
    db.flush()
    for r in extra:
        db.add(UserRole(user_id=user.id, role_id=r.id))
    if extra:
        db.flush()
        db.refresh(user)
    audit(db, actor, "user.create", "user", user.id,
          after={"username": user.username, "role": role.name, "roles": [r.name for r in user.all_roles]}, ip=client_ip(request))
    return user_out(user)


class UserPatch(BaseModel):
    is_active: bool | None = None
    role: str | None = None  # changes the PRIMARY role (the additional roles are kept)
    roles: list[str] | None = Field(None, max_length=10)  # the user's COMPLETE role set (replaces primary + additional roles)


@router.patch("/users/{user_id}")
def patch_user(user_id: UUID, body: UserPatch, request: Request,
               actor: User = Depends(require("users.manage")), db: DbSession = Depends(get_db, scope="function")):
    user = db.get(User, user_id)
    if not user:
        raise AppError("المستخدم غير موجود", 404, "not_found")
    before = {"is_active": user.is_active, "role": user.role.name, "roles": [r.name for r in user.all_roles]}
    # Never leave the system without an active administrator.
    db.execute(select(func.pg_advisory_xact_lock(7002)))  # serialise concurrent admin changes
    revoke = False
    if body.is_active is not None:
        if user.id == actor.id and not body.is_active:
            raise AppError("لا يمكنك تعطيل حسابك", 409, "self_disable")
        if not body.is_active and user.is_active:
            revoke = True
        user.is_active = body.is_active
    if body.role:
        role = db.scalar(select(Role).where(Role.name == body.role))
        if not role:
            raise AppError("الدور غير موجود", 422, "bad_role")
        if role.id != user.role_id:
            if user.id == actor.id:
                raise AppError("لا يمكنك تغيير دورك بنفسك", 409, "self_role_change")
            revoke = True
        user.role_id = role.id
        db.flush()
        db.refresh(user)
    if body.roles is not None:
        wanted = _resolve_roles(db, body.roles)
        if {r.id for r in wanted} != {r.id for r in user.all_roles} and user.id == actor.id:
            raise AppError("لا يمكنك تغيير دورك بنفسك", 409, "self_role_change")
        if _apply_roles(db, user, wanted):
            revoke = True
    db.flush()
    admin_role = db.scalar(select(Role).where(Role.name == "admin"))
    has_admin = or_(User.role_id == admin_role.id, User.id.in_(select(UserRole.user_id).where(UserRole.role_id == admin_role.id)))  # admin as primary OR additional role
    admins = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True), has_admin))
    if admins == 0:
        raise AppError("يجب أن يبقى مدير نظام فعّال واحد على الأقل", 409, "last_admin")  # rolls the whole change back
    if revoke:
        _revoke_sessions(db, user.id)  # the user signs in again with the new role / is logged out when disabled
    audit(db, actor, "user.update", "user", user.id, before=before,
          after={"is_active": user.is_active, "role": user.role.name, "roles": [r.name for r in user.all_roles]}, ip=client_ip(request))
    return user_out(user)


# ---- password management & role listing --------------------------------------------
class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LEN, max_length=200)


class ResetPassword(BaseModel):
    password: str = Field(min_length=MIN_PASSWORD_LEN, max_length=200)


def _revoke_sessions(db: DbSession, user_id, keep: str | None = None) -> None:
    for s in db.scalars(select(Session).where(Session.user_id == user_id)):
        if s.token_hash != keep:
            db.delete(s)


@router.post("/auth/change-password")
def change_password(body: ChangePassword, request: Request, user: User = Depends(current_user),
                    db: DbSession = Depends(get_db, scope="function")):
    if not verify_password(user.password_hash, body.current_password):
        audit(db, user, "password.change_failed", "user", user.id, ip=client_ip(request))
        db.commit()
        raise AppError("كلمة المرور الحالية غير صحيحة", 403, "bad_password")
    if body.new_password == body.current_password or body.new_password.lower() == user.username:
        raise AppError("اختر كلمة مرور جديدة مختلفة", 422, "weak_password")
    user.password_hash = hash_password(body.new_password)
    _revoke_sessions(db, user.id, keep=token_digest(request.cookies[COOKIE_NAME]))  # other devices must log in again
    audit(db, user, "password.change", "user", user.id, ip=client_ip(request))
    return {"ok": True}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: UUID, body: ResetPassword, request: Request,
                   actor: User = Depends(require("users.manage")), db: DbSession = Depends(get_db, scope="function")):
    user = db.get(User, user_id)
    if not user:
        raise AppError("المستخدم غير موجود", 404, "not_found")
    user.password_hash = hash_password(body.password)
    user.failed_attempts, user.locked_until = 0, None
    _revoke_sessions(db, user.id)
    audit(db, actor, "password.reset", "user", user.id, ip=client_ip(request))
    return {"ok": True}


@router.get("/roles")
def list_roles(_: User = Depends(require("users.manage")), db: DbSession = Depends(get_db, scope="function")):
    return [{"name": r.name, "label": r.label_ar, "permissions": sorted(p.permission for p in r.permissions)}
            for r in db.scalars(select(Role).order_by(Role.id))]
