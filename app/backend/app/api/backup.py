"""Backup / restore administration API (administrators only: permission backup.manage)."""
import secrets
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.backup import archive, restore, service
from app.backup.pgtools import BackupError
from app.core.audit import audit
from app.core.errors import AppError
from app.core.security import verify_password
from app.db import SessionLocal, get_db
from app.models import BackupRecord
from app.models.auth import User

router = APIRouter(prefix="/api", tags=["backup"])
perm = require("backup.manage")


def rec_out(r: BackupRecord) -> dict:
    v = r.verification or {}
    return {"id": str(r.id), "name": r.name, "trigger": r.trigger, "status": r.status, "encrypted": r.encrypted,
            "size_bytes": r.size_bytes, "sha256": r.sha256, "error": r.error, "created_at": r.created_at,
            "finished_at": r.finished_at, "checks": v.get("checks"), "schema": v.get("schema"),
            "created_manifest_at": (r.manifest or {}).get("created_at"), "row_counts": (r.manifest or {}).get("row_counts")}


def _get(db: DbSession, rid: UUID) -> BackupRecord:
    r = db.get(BackupRecord, rid)
    if not r:
        raise AppError("النسخة غير موجودة", 404, "not_found")
    return r


def _managed_path(db: DbSession, r: BackupRecord) -> Path:
    """Only archives inside the configured backup folder may be downloaded, verified or restored."""
    root = service.backup_dir(service.get_backup_settings(db)).resolve()
    p = Path(r.path).resolve()
    if p.parent != root or not p.is_file():
        raise AppError("ملف النسخة غير موجود في مجلد النسخ الاحتياطي", 404, "file_missing")
    return p


@router.get("/backups")
def dashboard(user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    cfg = service.get_backup_settings(db)
    directory = service.backup_dir(cfg)
    try:
        free = shutil.disk_usage(directory if directory.exists() else directory.anchor or ".").free
    except OSError:
        free = None
    now = datetime.now(timezone.utc)
    ok = db.scalar(select(BackupRecord).where(BackupRecord.status == "verified").order_by(BackupRecord.created_at.desc()).limit(1))
    bad = db.scalar(select(BackupRecord).where(BackupRecord.status == "failed").order_by(BackupRecord.created_at.desc()).limit(1))
    items = db.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(200))
    sch = cfg["schedule"]
    return {"directory": str(directory), "free_bytes": free, "settings": cfg,
            "last_success": rec_out(ok) if ok else None, "last_failure": rec_out(bad) if bad else None,
            "next_scheduled": service.next_slot(sch, now) if sch["enabled"] else None,
            "items": [rec_out(r) for r in items], "restore": restore.read_status()}


class CreateIn(BaseModel):
    passphrase: str | None = Field(None, min_length=8, max_length=200)


@router.post("/backups", status_code=202)
def create_backup(body: CreateIn, request: Request, user: User = Depends(perm)):
    with SessionLocal() as db:
        rec = BackupRecord(name="(in progress)", path="", trigger="manual", status="running", created_by=user.id,
                           encrypted=bool(body.passphrase))
        db.add(rec)
        db.commit()
        rid = rec.id
    threading.Thread(target=lambda: service.run_backup("manual", user.id, body.passphrase, record_id=rid),
                     name="manual-backup", daemon=True).start()
    return {"id": str(rid), "status": "running"}


@router.get("/backups/{rid}")
def get_backup(rid: UUID, _: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    return rec_out(_get(db, rid))


class VerifyIn(BaseModel):
    passphrase: str | None = None
    deep: bool = True


@router.post("/backups/{rid}/verify")
def verify_backup(rid: UUID, body: VerifyIn, request: Request, user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    r = _get(db, rid)
    _managed_path(db, r)
    db.commit()
    try:
        return rec_out(service.verify_record(rid, body.passphrase, body.deep, user))
    except BackupError as e:
        raise AppError(str(e), 409, "busy") from e


@router.get("/backups/{rid}/download")
def download(rid: UUID, request: Request, user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    r = _get(db, rid)
    p = _managed_path(db, r)
    audit(db, user, "backup.download", "backup", r.id, after={"name": r.name}, ip=client_ip(request))
    db.commit()
    return FileResponse(p, filename=r.name, media_type="application/octet-stream")


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3)


@router.post("/backups/{rid}/delete")
def delete_backup(rid: UUID, body: ReasonIn, user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    r = _get(db, rid)
    try:
        service.delete_backup(db, r, user, body.reason)
    except BackupError as e:
        raise AppError(str(e), 409, "last_valid_backup") from e
    return {"ok": True}


@router.post("/backups/rescan")
def rescan(user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    db.commit()
    n = service.rescan(service.backup_dir(service.get_backup_settings(db)))
    return {"registered": n}


@router.post("/backups/recovery-secret")
def recovery_secret(request: Request, user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    """A strong random passphrase, shown ONCE and never stored. Without it an encrypted backup cannot be recovered."""
    audit(db, user, "backup.recovery_secret_generated", "backup", None, ip=client_ip(request))
    return {"secret": secrets.token_urlsafe(24),
            "warning": "احفظ هذا السر في مكان آمن خارج الجهاز. لا يمكن استعادة نسخة مشفرة بدونه."}


# ---- settings ---------------------------------------------------------------
class ScheduleIn(BaseModel):
    enabled: bool
    frequency: str
    time: str
    weekday: int = 6
    day: int = 1


class RetentionIn(BaseModel):
    daily: int
    weekly: int
    monthly: int


class SettingsIn(BaseModel):
    dir: str | None = None
    schedule: ScheduleIn
    retention: RetentionIn
    encrypt_scheduled: bool = False
    deep_verify: bool = True


@router.put("/backup-settings")
def save_settings(body: SettingsIn, request: Request, user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    from app.models import AppSetting
    cfg = {"dir": (body.dir or "").strip() or None, "schedule": body.schedule.model_dump(),
           "retention": body.retention.model_dump(), "encrypt_scheduled": body.encrypt_scheduled,
           "deep_verify": body.deep_verify}
    try:
        service.validate_settings(cfg)
        if cfg["dir"]:
            p = Path(cfg["dir"])
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".write-test"
            probe.write_bytes(b"ok")
            probe.unlink()
    except BackupError as e:
        raise AppError(str(e), 422, "bad_settings") from e
    except OSError as e:
        raise AppError("لا يمكن الكتابة في مجلد النسخ الاحتياطي المحدد", 422, "bad_directory") from e
    row = db.get(AppSetting, "backup")
    before = row.value if row else None
    if row:
        row.value = cfg
    else:
        db.add(AppSetting(key="backup", value=cfg))
    audit(db, user, "backup.settings", "settings", "backup", before=before, after=cfg, ip=client_ip(request))
    return cfg


# ---- restore -------------------------------------------------------------------
class PreviewIn(BaseModel):
    id: UUID
    passphrase: str | None = None


@router.post("/restore/preview")
def restore_preview(body: PreviewIn, _: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    p = _managed_path(db, _get(db, body.id))
    return restore.preview(p, body.passphrase)


class RestoreIn(BaseModel):
    id: UUID
    passphrase: str | None = None
    confirm: str
    admin_password: str


@router.post("/restore", status_code=202)
def start_restore(body: RestoreIn, request: Request, user: User = Depends(perm), db: DbSession = Depends(get_db, scope="function")):
    if body.confirm != "RESTORE":
        raise AppError("اكتب RESTORE للتأكيد", 422, "not_confirmed")
    if not verify_password(user.password_hash, body.admin_password):  # destructive: re-authenticate
        audit(db, user, "restore.denied", "backup", body.id, after={"reason": "bad password"}, ip=client_ip(request))
        db.commit()
        raise AppError("كلمة مرور المدير غير صحيحة", 403, "bad_password")
    r = _get(db, body.id)
    p = _managed_path(db, r)
    if restore.read_status().get("state") == "running":
        raise AppError("هناك استعادة جارية", 409, "busy")
    audit(db, user, "restore.start", "backup", r.id, after={"name": r.name}, ip=client_ip(request))
    db.commit()
    uid = user.id

    def work():
        try:
            restore.restore_backup(p, body.passphrase, uid)
        except Exception:  # noqa: BLE001 - outcome is in the status file
            pass

    threading.Thread(target=work, name="restore", daemon=True).start()
    return {"started": True}


@router.get("/restore/status")
def restore_status():
    """Public and minimal on purpose: the session store is replaced by a restore, so users must still see progress."""
    st = restore.read_status()
    return {"state": st.get("state"),
            "steps": [{key: step.get(key) for key in ("key", "label", "status")}
                      for step in st.get("steps", []) if isinstance(step, dict)],
            "error": None}  # raw error/detail fields can contain private paths and database names
