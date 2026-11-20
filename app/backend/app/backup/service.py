"""Backup operations with records, settings, locking, retention and the scheduler logic."""
import logging
import os
import shutil
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.backup import archive
from app.backup.pgtools import BackupError
from app.core.audit import audit
from app.core.config import get_settings
from app.db import SessionLocal
from app.models import AppSetting, BackupRecord
from app.models.auth import User

TZ = ZoneInfo("Asia/Qatar")
DEFAULTS = {
    "dir": None,  # None => <storage>/backups
    "schedule": {"enabled": True, "frequency": "daily", "time": "02:00", "weekday": 6, "day": 1},
    "retention": {"daily": 7, "weekly": 4, "monthly": 12},
    "encrypt_scheduled": False,
    "deep_verify": True,
}
_thread_lock = threading.Lock()
_log = logging.getLogger("uvicorn.error")  # the Windows service routes this logger to storage/logs/service.log


# ---------------------------------------------------------------- settings
def get_backup_settings(db) -> dict:
    row = db.get(AppSetting, "backup")
    merged = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    if row:
        for k, v in row.value.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
    return merged


def validate_settings(cfg: dict) -> dict:
    sch, ret = cfg["schedule"], cfg["retention"]
    if sch["frequency"] not in ("daily", "weekly", "monthly"):
        raise BackupError("تكرار غير صحيح")
    try:
        hh, mm = sch["time"].split(":")
        assert 0 <= int(hh) < 24 and 0 <= int(mm) < 60
    except Exception as e:  # noqa: BLE001
        raise BackupError("وقت غير صحيح (مثال 02:00)") from e
    if not (0 <= int(sch["weekday"]) <= 6) or not (1 <= int(sch["day"]) <= 28):
        raise BackupError("يوم غير صحيح")
    for k in ("daily", "weekly", "monthly"):
        if not (0 <= int(ret[k]) <= 365):
            raise BackupError("قيمة الاحتفاظ غير صحيحة")
    if int(ret["daily"]) + int(ret["weekly"]) + int(ret["monthly"]) < 1:
        raise BackupError("يجب الاحتفاظ بنسخة واحدة على الأقل")
    return cfg


def backup_dir(cfg: dict) -> Path:
    return Path(cfg["dir"]) if cfg.get("dir") else get_settings().storage_dir / "backups"


# ---------------------------------------------------------------- locking (one backup/restore at a time, across processes)
@contextmanager
def operation_lock(name: str = "backup"):
    path = get_settings().storage_dir / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not _thread_lock.acquire(blocking=False):
        raise BackupError("هناك عملية نسخ احتياطي أو استعادة جارية الآن")
    fd = None
    try:
        for _ in range(2):
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {time.time()}".encode())
                break
            except FileExistsError:
                try:
                    stale = time.time() - path.stat().st_mtime > 6 * 3600
                except FileNotFoundError:
                    continue
                if not stale:
                    raise BackupError("هناك عملية نسخ احتياطي أو استعادة جارية الآن")
                path.unlink(missing_ok=True)
        if fd is None:
            raise BackupError("تعذر الحصول على قفل العملية")
        yield
    finally:
        if fd is not None:
            os.close(fd)
            path.unlink(missing_ok=True)
        _thread_lock.release()


# ---------------------------------------------------------------- running a backup
def run_backup(trigger: str, user_id=None, passphrase: str | None = None, record_id=None,
               prefix: str = "AutoCarePro_Backup", dir_override: Path | None = None, deep: bool | None = None) -> BackupRecord:
    """Create + verify a backup and keep a record of the outcome. Status 'verified' is only set after verification."""
    with SessionLocal() as db:
        cfg = get_backup_settings(db)
        target = Path(dir_override) if dir_override else backup_dir(cfg)
        use_deep = cfg["deep_verify"] if deep is None else deep
        rec = db.get(BackupRecord, record_id) if record_id else None
        if rec is None:
            rec = BackupRecord(name="(in progress)", path="", trigger=trigger, created_by=user_id, status="running")
            db.add(rec)
        db.commit()
        rid = rec.id
    try:
        with operation_lock("backup"):
            result = archive.create_archive(target, trigger, passphrase, deep=use_deep, prefix=prefix)
    except BaseException as e:  # noqa: BLE001 - recorded, then re-raised for callers that care
        with SessionLocal() as db:
            rec = db.get(BackupRecord, rid)
            rec.status, rec.error, rec.finished_at = "failed", str(e)[:1000], datetime.now(timezone.utc)
            audit(db, db.get(User, user_id) if user_id else None, "backup.failed", "backup", rid, after={"error": str(e)[:300]})
            db.commit()
        if isinstance(e, BackupError):
            return _load(rid)
        raise
    with SessionLocal() as db:
        rec = db.get(BackupRecord, rid)
        p = Path(result["path"])
        rec.name, rec.path, rec.status = p.name, str(p), "verified"
        rec.encrypted = p.name.endswith(".enc")
        rec.size_bytes, rec.sha256 = result["size"], result["sha256"]
        rec.manifest, rec.verification, rec.finished_at = result["manifest"], result["verification"], datetime.now(timezone.utc)
        audit(db, db.get(User, user_id) if user_id else None, "backup.create", "backup", rid,
              after={"name": p.name, "size": rec.size_bytes, "trigger": trigger, "encrypted": rec.encrypted})
        db.commit()
    if trigger == "schedule":
        with SessionLocal() as db:
            apply_retention(db)
            db.commit()
    return _load(rid)


def _load(rid) -> BackupRecord:
    with SessionLocal() as db:
        return db.get(BackupRecord, rid)


def recover_interrupted() -> int:
    """On startup: mark backups left in 'running' as failed and remove their debris."""
    with SessionLocal() as db:
        cfg = get_backup_settings(db)
        n = archive.cleanup_leftovers(backup_dir(cfg))
        for rec in db.scalars(select(BackupRecord).where(BackupRecord.status == "running")):
            rec.status, rec.error, rec.finished_at = "failed", "توقفت العملية قبل الاكتمال (انقطاع)", datetime.now(timezone.utc)
            n += 1
        db.commit()
    return n


# ---------------------------------------------------------------- retention
def select_for_deletion(records: list[dict], policy: dict, now: datetime | None = None) -> list[str]:
    """Pure function. records: [{id, created_at(datetime), trigger, status}] -> ids that may be deleted.

    Keeps the newest verified backup of each of the last N days / ISO weeks / months (per policy), never the last verified
    backup, and never anything unverified (those are handled by the caller). Pre-restore safety backups are kept 90 days.
    """
    now = now or datetime.now(timezone.utc)
    verified = sorted((r for r in records if r["status"] == "verified"), key=lambda r: r["created_at"], reverse=True)
    regular = [r for r in verified if r["trigger"] in ("manual", "schedule", "imported")]
    keep: set[str] = set()
    if verified:
        keep.add(verified[0]["id"])  # never delete the most recent valid backup
    if regular:
        keep.add(regular[0]["id"])

    def local(r):
        return r["created_at"].astimezone(TZ)

    def bucket(key_fn, limit):
        seen = []
        for r in regular:
            k = key_fn(local(r))
            if k not in seen:
                seen.append(k)
                if len(seen) <= limit:
                    keep.add(r["id"])
    bucket(lambda d: d.date(), policy["daily"])
    bucket(lambda d: d.isocalendar()[:2], policy["weekly"])
    bucket(lambda d: (d.year, d.month), policy["monthly"])
    out = []
    for r in verified:
        if r["id"] in keep:
            continue
        if r["trigger"] == "pre_restore" and now - r["created_at"] < timedelta(days=90):
            continue
        out.append(r["id"])
    return out


def apply_retention(db) -> list[str]:
    cfg = get_backup_settings(db)
    recs = list(db.scalars(select(BackupRecord).where(BackupRecord.finished_at.is_not(None))))
    view = [{"id": str(r.id), "created_at": r.created_at, "trigger": r.trigger, "status": r.status} for r in recs]
    doomed = set(select_for_deletion(view, cfg["retention"]))
    deleted = []
    root = backup_dir(cfg).resolve()
    for r in recs:
        if str(r.id) in doomed:
            p = Path(r.path)
            try:
                if p.resolve().parent == root and p.is_file():  # only ever delete our own files inside the backup folder
                    p.unlink()
            except OSError:
                continue
            deleted.append(r.name)
            db.delete(r)
    # failed attempts older than a week are just clutter
    for r in recs:
        if r.status == "failed" and r.finished_at and datetime.now(timezone.utc) - r.finished_at > timedelta(days=7):
            db.delete(r)
    if deleted:
        audit(db, None, "backup.retention", "backup", None, after={"deleted": deleted})
    return deleted


def delete_backup(db, rec: BackupRecord, user: User, reason: str) -> None:
    """Manual delete; the last valid backup can never be removed."""
    others = db.scalar(select(BackupRecord.id).where(BackupRecord.status == "verified", BackupRecord.id != rec.id).limit(1))
    if rec.status == "verified" and others is None:
        raise BackupError("لا يمكن حذف النسخة الصالحة الوحيدة")
    root = backup_dir(get_backup_settings(db)).resolve()
    p = Path(rec.path)
    if rec.path and p.resolve().parent == root and p.is_file():
        p.unlink()
    audit(db, user, "backup.delete", "backup", rec.id, before={"name": rec.name}, reason=reason)
    db.delete(rec)


# ---------------------------------------------------------------- schedule maths (pure)
def prev_slot(sch: dict, now: datetime) -> datetime:
    """The most recent scheduled run time at or before `now` (Qatar local time)."""
    now = now.astimezone(TZ)
    hh, mm = map(int, sch["time"].split(":"))
    if sch["frequency"] == "daily":
        slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return slot if slot <= now else slot - timedelta(days=1)
    if sch["frequency"] == "weekly":
        slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0) - timedelta(days=(now.weekday() - int(sch["weekday"])) % 7)
        return slot if slot <= now else slot - timedelta(days=7)
    slot = now.replace(day=int(sch["day"]), hour=hh, minute=mm, second=0, microsecond=0)
    if slot <= now:
        return slot
    prev = (now.replace(day=1) - timedelta(days=1)).replace(day=int(sch["day"]), hour=hh, minute=mm, second=0, microsecond=0)
    return prev


def next_slot(sch: dict, now: datetime) -> datetime:
    p = prev_slot(sch, now)
    if sch["frequency"] == "daily":
        return p + timedelta(days=1)
    if sch["frequency"] == "weekly":
        return p + timedelta(days=7)
    nxt = (p.replace(day=28) + timedelta(days=4)).replace(day=int(sch["day"]))
    return nxt


def is_due(sch: dict, last_success: datetime | None, now: datetime) -> bool:
    """True when the latest scheduled slot has passed without a successful backup (also catches up missed runs)."""
    if not sch.get("enabled"):
        return False
    return last_success is None or last_success.astimezone(TZ) < prev_slot(sch, now)


def last_success(db, triggers=("schedule", "manual")) -> datetime | None:
    row = db.scalar(select(BackupRecord.created_at).where(BackupRecord.status == "verified", BackupRecord.trigger.in_(triggers))
                    .order_by(BackupRecord.created_at.desc()).limit(1))
    return row


def scheduler_tick(now: datetime | None = None, passphrase: str | None = None) -> BackupRecord | None:
    """Run a scheduled backup if one is due. Safe to call often."""
    now = now or datetime.now(timezone.utc)
    with SessionLocal() as db:
        cfg = get_backup_settings(db)
        last = last_success(db)
        running = db.scalar(select(BackupRecord.id).where(BackupRecord.status == "running", BackupRecord.created_at > now - timedelta(hours=6)).limit(1))
        # do not retry a failed scheduled attempt in a tight loop: wait 30 minutes after a failure
        failed_recent = db.scalar(select(BackupRecord.id).where(BackupRecord.status == "failed", BackupRecord.trigger == "schedule",
                                                                BackupRecord.created_at > now - timedelta(minutes=30)).limit(1))
    if running or failed_recent or not is_due(cfg["schedule"], last, now):
        return None
    pw = None
    if cfg["encrypt_scheduled"]:
        pw = passphrase or os.environ.get("AUTOCARE_BACKUP_PASSPHRASE")
        if not pw:
            pf = get_settings().storage_dir / "secrets" / "backup.pass"
            pw = pf.read_text(encoding="utf-8").strip() if pf.exists() else None
        if not pw:
            # Do not fail silently: leave a visible failed record (the 30-minute back-off above stops this repeating every minute).
            msg = "النسخ المجدولة المشفرة تحتاج كلمة سر محفوظة، لذلك لم يتم أخذ نسخة"
            with SessionLocal() as db:
                db.add(BackupRecord(name="(scheduled backup not run)", path="", trigger="schedule", status="failed",
                                    error=msg, finished_at=datetime.now(timezone.utc)))
                audit(db, None, "backup.failed", "backup", None, after={"error": msg})
                db.commit()
            _log.error("scheduled backup skipped: %s", msg)
            return None
    return run_backup("schedule", None, pw)


_stop = threading.Event()


def start_scheduler() -> threading.Thread | None:
    if get_settings().disable_scheduler:
        return None

    def loop():
        try:
            recover_interrupted()
        except Exception:  # noqa: BLE001
            _log.exception("backup recovery at startup failed")
        while not _stop.wait(60):
            try:
                scheduler_tick()
            except Exception:  # noqa: BLE001 - never let the scheduler thread die, but never hide the reason either
                _log.exception("scheduled backup check failed")

    t = threading.Thread(target=loop, name="backup-scheduler", daemon=True)
    t.start()
    return t


def stop_scheduler() -> None:
    _stop.set()


# ---------------------------------------------------------------- index maintenance
def rescan(directory: Path) -> int:
    """Register archives found on disk that have no record (after a restore or when moving to a new computer)."""
    directory = Path(directory)
    if not directory.exists():
        return 0
    n = 0
    with SessionLocal() as db:
        known = {r.path for r in db.scalars(select(BackupRecord))}
        for p in sorted(list(directory.glob("AutoCarePro_*.zip")) + list(directory.glob("AutoCarePro_*.zip.enc"))):
            if str(p) in known:
                continue
            manifest, created = None, datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            enc = p.name.endswith(".enc")
            if not enc:
                try:
                    import zipfile
                    with zipfile.ZipFile(p) as zf:
                        manifest = archive.read_manifest(zf)
                    created = datetime.fromisoformat(manifest["created_at"])
                except Exception:  # noqa: BLE001 - unreadable archives are still listed, as unverified
                    manifest = None
            db.add(BackupRecord(name=p.name, path=str(p), trigger="pre_restore" if "_PreRestore_" in p.name else "imported",
                                status="unverified", encrypted=enc, size_bytes=p.stat().st_size, sha256=archive.sha256_file(p),
                                manifest=manifest, created_at=created, finished_at=datetime.now(timezone.utc)))
            n += 1
        db.commit()
    return n


def verify_record(rid, passphrase: str | None = None, deep: bool = True, user: User | None = None) -> BackupRecord:
    """Re-verify an existing archive; a backup that no longer verifies stops counting as a valid backup."""
    with SessionLocal() as db:
        rec = db.get(BackupRecord, rid)
        path = Path(rec.path)
    with operation_lock("backup"):
        res = archive.verify_archive(path, passphrase, deep=deep)
    with SessionLocal() as db:
        rec = db.get(BackupRecord, rid)
        rec.verification = res
        if res.get("manifest"):
            rec.manifest = res["manifest"]
        rec.status = "verified" if res["ok"] else "failed"
        rec.error = None if res["ok"] else "; ".join(c["detail"] for c in res["checks"] if not c["ok"])[:1000]
        audit(db, user, "backup.verify", "backup", rid, after={"ok": res["ok"]})
        db.commit()
    return _load(rid)
