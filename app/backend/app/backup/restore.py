"""Guided, safe restore: verify -> safety backup -> maintenance mode -> restore into a NEW database ->
migrate/verify -> swap names (with rollback) -> swap attachment folders -> post-checks.

The live database is never modified in place: it is renamed aside (kept as <name>_old_<timestamp>) only after the
restored copy has been fully verified, and the rename is reverted automatically if anything fails afterwards."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.backup import archive, pgtools, service
from app.backup.pgtools import BackupError
from app.core import maintenance
from app.core.audit import audit
from app.core.config import BACKEND_DIR, get_settings
from app.db import SessionLocal, engine
from app.models import AuditLog, BackupRecord

STEPS = [("select", "اختيار النسخة"), ("verify", "فحص النسخة والتوافق"), ("safety_backup", "نسخة أمان من الوضع الحالي"),
         ("maintenance", "تفعيل وضع الصيانة"), ("restore", "استعادة البيانات والملفات"),
         ("verify_restored", "فحص النظام بعد الاستعادة"), ("finish", "إنهاء")]


def status_path() -> Path:
    return get_settings().storage_dir / "restore-status.json"


def read_status() -> dict:
    try:
        return json.loads(status_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": "idle", "steps": []}


class _Status:
    def __init__(self):
        self.data = {"state": "running", "started_at": datetime.now(timezone.utc).isoformat(), "finished_at": None,
                     "error": None, "old_database": None, "steps": [{"key": k, "label": l, "status": "pending", "detail": ""} for k, l in STEPS]}
        self.flush()

    def flush(self):
        p = status_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        for attempt in range(50):  # Windows refuses the replace while a status poll has the file open
            try:
                os.replace(tmp, p)
                return
            except PermissionError:
                if attempt == 49:
                    raise
                time.sleep(0.05)

    def step(self, key: str, status: str, detail: str = ""):
        for s in self.data["steps"]:
            if s["key"] == key:
                s["status"], s["detail"] = status, detail
        self.flush()

    def finish(self, state: str, error: str | None = None):
        self.data.update(state=state, error=error, finished_at=datetime.now(timezone.utc).isoformat())
        self.flush()


def preview(path: Path, passphrase: str | None, deep: bool = False) -> dict:
    res = archive.verify_archive(path, passphrase, deep=deep)
    m = res.get("manifest") or {}
    return {"ok": res["ok"], "checks": res["checks"], "schema": res["schema"], "needs_upgrade": res["needs_upgrade"],
            "created_at": m.get("created_at"), "app_version": m.get("app_version"), "row_counts": m.get("row_counts"),
            "encrypted": bool(path.is_file() and archive.crypto.is_encrypted(path))}


def _counts(url, database: str) -> dict:
    eng = create_engine(pgtools.with_database(url, database), poolclass=NullPool)
    try:
        with eng.connect() as c:
            out = {t: c.execute(text(f"select count(*) from {t}")).scalar() for t in archive.COUNT_TABLES}
            out["_rev"] = c.execute(text("select version_num from alembic_version")).scalar()
        return out
    finally:
        eng.dispose()


def _extract_files(zip_path: Path, staging: Path) -> None:
    """Extract only files/<dir>/... with strict path checks (no traversal, no symlinks)."""
    root = staging.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.filename.endswith("/") or not info.filename.startswith("files/"):
                continue
            if not archive.safe_member_name(info.filename) or archive._is_symlink(info):
                raise BackupError("مسار غير آمن داخل النسخة")
            dest = (staging / info.filename[len("files/"):]).resolve()
            if root not in dest.parents:
                raise BackupError("محاولة الكتابة خارج مجلد الاستعادة")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out, 1024 * 1024)


def _migrate(url, database: str) -> None:
    target = pgtools.with_database(url, database).render_as_string(hide_password=False)
    env = os.environ.copy()
    env["AUTOCARE_MIGRATE_URL"] = target
    proc = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR, env=env, capture_output=True)
    if proc.returncode != 0:
        raise BackupError("فشل ترقية قاعدة البيانات المستعادة: " + proc.stderr.decode("utf-8", "replace")[-300:])


def restore_backup(path: Path, passphrase: str | None, user_id=None, url=None) -> dict:
    """Run a full restore. Raises BackupError on failure after rolling back to the previous state."""
    url = pgtools.db_url(url)
    live = url.database
    path = Path(path)
    st = _Status()
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    new_db, old_db = f"{live}_restore_{ts}", f"{live}_old_{ts}"
    storage = get_settings().storage_dir
    workdir = None
    swapped_db = swapped_files = False
    moved: list[tuple[Path, Path]] = []  # (original, set-aside) for attachment folders
    placed: list[Path] = []              # restored folders put in place (removed again on rollback)
    safety = None
    live_exists = False
    try:
        with service.operation_lock("backup"):
            st.step("select", "running")
            if not path.is_file():
                raise BackupError("ملف النسخة غير موجود")
            st.step("select", "done", path.name)
            # --- verify (deep: includes a test restore in a temporary database)
            st.step("verify", "running")
            res = archive.verify_archive(path, passphrase, deep=True, url=url)
            if not res["ok"]:
                bad = [c for c in res["checks"] if not c["ok"]]
                raise BackupError("النسخة لم تجتز الفحص، لم يتم تغيير أي شيء: " + "; ".join(f"{c['name']}: {c['detail']}" for c in bad))
            manifest, needs_upgrade = res["manifest"], res["needs_upgrade"]
            st.step("verify", "done", "ترقية قاعدة البيانات مطلوبة" if needs_upgrade else "النسخة سليمة ومتوافقة")
            live_exists = pgtools.database_exists(url, live)
            # --- safety backup of what is running now
            st.step("safety_backup", "running")
            if live_exists:
                cfg_dir = service.backup_dir(_settings_snapshot())
                safety = archive.create_archive(cfg_dir, "pre_restore", None, url=url, deep=True, prefix="AutoCarePro_PreRestore")
                st.step("safety_backup", "done", Path(safety["path"]).name)
            else:
                st.step("safety_backup", "skipped", "قاعدة البيانات الحالية غير موجودة")
            # --- maintenance mode: stop writes, drop connections
            st.step("maintenance", "running")
            maintenance.enter("restore")
            engine.dispose()
            time.sleep(1.0)
            st.step("maintenance", "done")
            # --- restore into a fresh database
            st.step("restore", "running")
            workdir = Path(tempfile.mkdtemp(prefix="acrestore-", dir=storage if storage.exists() else None))
            zip_path = archive.open_archive(path, passphrase, workdir)
            with zipfile.ZipFile(zip_path) as zf, zf.open("database.dump") as src, open(workdir / "database.dump", "wb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            _extract_files(zip_path, workdir / "files")
            pgtools.create_database(url, new_db)
            pgtools.pg_restore(url, workdir / "database.dump", new_db)
            if needs_upgrade:
                _migrate(url, new_db)
            expected = dict(manifest["row_counts"])
            got = _counts(url, new_db)
            head, _ = archive.alembic_revisions()
            diff = {t: (got[t], expected[t]) for t in expected if got[t] != expected[t]}
            if diff or got["_rev"] != head:
                raise BackupError(f"البيانات المستعادة لا تطابق النسخة: {diff or got['_rev']}")
            eng = create_engine(pgtools.with_database(url, new_db), poolclass=NullPool)
            with eng.begin() as c:
                c.execute(text("delete from sessions"))  # everybody must log in again after a restore
            eng.dispose()
            # swap database names (old one kept for recovery)
            if live_exists:
                pgtools.rename_database(url, live, old_db)
            try:
                pgtools.rename_database(url, new_db, live)
            except Exception:
                if live_exists:
                    pgtools.rename_database(url, old_db, live)
                raise
            swapped_db = True
            # swap attachment folders
            for d in archive.STORAGE_DIRS:
                cur = storage / d
                if cur.exists():
                    aside = storage / f"{d}.pre-restore-{ts}"
                    cur.rename(aside)
                    moved.append((cur, aside))
                new = workdir / "files" / d
                if new.exists():
                    shutil.move(str(new), str(cur))
                    placed.append(cur)
            swapped_files = True
            st.step("restore", "done", f"النسخة السابقة محفوظة باسم {old_db}" if live_exists else "")
            # --- post checks on the live system
            st.step("verify_restored", "running")
            engine.dispose()
            final = _counts(url, live)
            diff = {t: (final[t], expected[t]) for t in expected if final[t] != expected[t]}
            if diff or final["_rev"] != head:
                raise BackupError(f"فحص ما بعد الاستعادة فشل: {diff or final['_rev']}")
            st.step("verify_restored", "done", "تطابقت الأعداد وإصدار قاعدة البيانات")
            with SessionLocal() as db:
                cfg = service.get_backup_settings(db)
                try:
                    service.backup_dir(cfg).mkdir(parents=True, exist_ok=True)
                except OSError:  # settings came from another computer: fall back to the default folder
                    from app.models import AppSetting
                    row = db.get(AppSetting, "backup")
                    if row:
                        row.value = {**row.value, "dir": None}
                if safety:  # the index of backups lives in the database that was just replaced: re-register the safety copy
                    sb = safety
                    db.add(BackupRecord(name=Path(sb["path"]).name, path=sb["path"], trigger="pre_restore", status="verified",
                                        size_bytes=sb["size"], sha256=sb["sha256"], manifest=sb["manifest"],
                                        verification=sb["verification"], created_by=user_id, finished_at=datetime.now(timezone.utc)))
                audit(db, None, "restore.complete", "backup", None,
                      after={"archive": path.name, "previous_database": old_db if live_exists else None,
                             "safety_backup": True, "counts": expected})
                db.commit()
            service.rescan(service.backup_dir(_settings_snapshot()))
            st.step("finish", "done")
            st.data["old_database"] = old_db if live_exists else None
            st.finish("done")
            return {"ok": True, "previous_database": old_db if live_exists else None, "counts": expected}
    except BaseException as e:  # noqa: BLE001
        # roll back to the previous operational state
        try:
            for cur in placed:
                shutil.rmtree(cur, ignore_errors=True)
            for cur, aside in reversed(moved):
                if cur.exists():
                    shutil.rmtree(cur, ignore_errors=True)
                aside.rename(cur)
            if swapped_db:
                engine.dispose()
                failed_name = f"{live}_failed_{ts}"
                pgtools.rename_database(url, live, failed_name)
                if live_exists:
                    pgtools.rename_database(url, old_db, live)
            else:
                pgtools.drop_database(url, new_db)
        except Exception:  # noqa: BLE001
            pass
        if not isinstance(e, BackupError):  # keep the technical details for support, never show them in the UI
            import logging
            import traceback
            logging.getLogger("autocare.restore").exception("unexpected restore failure")
            try:
                (storage / "restore-last-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            except OSError:
                pass
        msg = str(e) if isinstance(e, BackupError) else "حدث خطأ غير متوقع أثناء الاستعادة"
        st.finish("rolled_back" if (swapped_db or swapped_files) else "failed", msg)
        for s in st.data["steps"]:
            if s["status"] == "running":
                s["status"], s["detail"] = "failed", msg
        st.flush()
        if isinstance(e, BackupError):
            raise
        raise BackupError(msg) from e
    finally:
        maintenance.leave()
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def _settings_snapshot() -> dict:
    try:
        with SessionLocal() as db:
            return service.get_backup_settings(db)
    except Exception:  # noqa: BLE001 - e.g. app_settings missing in a very old database
        return {**service.DEFAULTS}
