"""Create and verify backup archives.

Archive (zip, optionally AES-GCM encrypted) contains:
  manifest.json   format, versions, alembic revision, row counts, sha256 + size of every other file
  database.dump   pg_dump custom format taken from one exported snapshot (transactionally consistent)
  config.json     non-secret application configuration (secrets such as passwords are never included)
  files/...       copies of the attachment / generated-document folders
"""
import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.backup import crypto, pgtools
from app.backup.pgtools import BackupError
from app.core.config import BACKEND_DIR, get_settings
from app.version import APP_VERSION

FORMAT_VERSION = 1
COUNT_TABLES = ["users", "customers", "vehicles", "vehicle_visits", "part_purchases", "quotations", "invoices",
                "payments", "expenses", "audit_logs"]
EXCLUDE_DATA = ["backup_records"]
STORAGE_DIRS = ["attachments", "generated"]
TOP_FILES = {"manifest.json", "database.dump", "config.json"}
MAX_MANIFEST = 20 * 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def alembic_revisions() -> tuple[str, set[str]]:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    return script.get_current_head(), {s.revision for s in script.walk_revisions()}


def schema_compat(revision: str | None) -> str:
    head, known = alembic_revisions()
    if revision == head:
        return "current"
    return "older" if revision in known else "incompatible"


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.exists() else 0


def storage_roots() -> list[Path]:
    root = get_settings().storage_dir
    return [root / d for d in STORAGE_DIRS]


# ---------------------------------------------------------------------------- create
def create_archive(backup_dir: Path, trigger: str, passphrase: str | None = None, url=None, deep: bool = True,
                   prefix: str = "AutoCarePro_Backup") -> dict:
    """Build, finalize and verify an archive. Returns {path, size, sha256, manifest, verification}."""
    url = pgtools.db_url(url)
    backup_dir = Path(backup_dir)
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        probe = backup_dir / f".write-test-{uuid.uuid4().hex}"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as e:
        raise BackupError(f"مجلد النسخ الاحتياطي غير متاح للكتابة: {e}") from e

    staging = backup_dir / f".staging-{uuid.uuid4().hex}"
    partial = None
    final = None
    try:
        # 1. storage check
        eng = create_engine(url, isolation_level="REPEATABLE READ", poolclass=NullPool)
        with eng.connect() as conn:
            db_size = conn.execute(text("select pg_database_size(current_database())")).scalar()
            files_size = sum(_dir_size(r) for r in storage_roots())
            need = int((db_size + files_size) * 2.2) + 64 * 1024 * 1024
            free = shutil.disk_usage(backup_dir).free
            if free < need:
                raise BackupError(f"المساحة الفارغة غير كافية ({free // 2**20} ميجا متاحة، المطلوب {need // 2**20} ميجا)")
            conn.rollback()
        staging.mkdir()
        # 2. consistent snapshot: counts + pg_dump read the very same snapshot
        with eng.connect() as conn:
            snap = conn.execute(text("select pg_export_snapshot()")).scalar()
            counts = {t: conn.execute(text(f"select count(*) from {t}")).scalar() for t in COUNT_TABLES}
            revision = conn.execute(text("select version_num from alembic_version")).scalar()
            pg_ver = conn.execute(text("show server_version")).scalar()
            pgtools.pg_dump(url, staging / "database.dump", snap, EXCLUDE_DATA)
            conn.rollback()
        eng.dispose()
        # 3. attachments and configuration
        for root in storage_roots():
            if root.exists():
                shutil.copytree(root, staging / "files" / root.name)
        s = get_settings()
        (staging / "config.json").write_text(json.dumps({
            "app_version": APP_VERSION, "session_minutes": s.session_minutes, "max_failed_logins": s.max_failed_logins,
            "lockout_minutes": s.lockout_minutes, "cookie_secure": s.cookie_secure,
            "note": "Secrets (database password, secret key) are intentionally NOT included; keep your .env file safe separately."},
            ensure_ascii=False, indent=2), encoding="utf-8")
        # 4. manifest with checksums of every file
        files = []
        for f in sorted(p for p in staging.rglob("*") if p.is_file()):
            files.append({"path": f.relative_to(staging).as_posix(), "size": f.stat().st_size, "sha256": sha256_file(f)})
        manifest = {"format_version": FORMAT_VERSION, "app": "AutoCare Pro", "app_version": APP_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(), "trigger": trigger,
                    "database": url.database, "pg_server_version": pg_ver, "alembic_revision": revision,
                    "row_counts": counts, "excluded_table_data": EXCLUDE_DATA, "files": files}
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        # 5. package (zip), then optionally encrypt; write under a temporary name, rename when complete
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        ext = ".zip.enc" if passphrase else ".zip"
        final = backup_dir / f"{prefix}_{stamp}{ext}"
        n = 2
        while final.exists():  # never overwrite an existing backup
            final = backup_dir / f"{prefix}_{stamp}_{n}{ext}"
            n += 1
        partial = backup_dir / (final.name + ".partial")
        zip_path = backup_dir / f".zip-{uuid.uuid4().hex}.tmp"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(staging / "manifest.json", "manifest.json")
            for f in files:
                zf.write(staging / f["path"], f["path"])
        if passphrase:
            crypto.encrypt_file(zip_path, partial, passphrase)
            zip_path.unlink()
        else:
            os.replace(zip_path, partial)
        os.replace(partial, final)
        partial = None
        shutil.rmtree(staging, ignore_errors=True)
        # 6. verify what is actually on disk; only then is the backup considered successful
        verification = verify_archive(final, passphrase, deep=deep, url=url)
        if not verification["ok"]:
            failed = [c for c in verification["checks"] if not c["ok"]]
            raise BackupError("فشل التحقق من النسخة: " + "; ".join(f"{c['name']}: {c['detail']}" for c in failed))
        return {"path": str(final), "size": final.stat().st_size, "sha256": sha256_file(final), "manifest": manifest,
                "verification": verification}
    except BaseException:
        # interrupted or failed: leave no half-written archive behind (earlier backups are never touched)
        shutil.rmtree(staging, ignore_errors=True)
        for leftover in (partial, final):
            if leftover is not None:
                try:
                    Path(leftover).unlink()
                except FileNotFoundError:
                    pass
        for tmp in backup_dir.glob(".zip-*.tmp"):
            tmp.unlink(missing_ok=True)
        raise


def cleanup_leftovers(backup_dir: Path) -> int:
    """Remove debris from backups that were killed mid-way (call on startup)."""
    n = 0
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return 0
    for p in list(backup_dir.glob(".staging-*")):
        shutil.rmtree(p, ignore_errors=True)
        n += 1
    for p in list(backup_dir.glob("*.partial")) + list(backup_dir.glob(".zip-*.tmp")):
        p.unlink(missing_ok=True)
        n += 1
    return n


# ---------------------------------------------------------------------------- verify
def safe_member_name(name: str) -> bool:
    if not name or name.startswith(("/", "\\")) or "\\" in name or ":" in name or "\x00" in name:
        return False
    parts = name.rstrip("/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    return name in TOP_FILES or name.startswith("files/")


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(info.external_attr >> 16)


def open_archive(path: Path, passphrase: str | None, workdir: Path) -> Path:
    """Return a path to a plain zip (decrypting into workdir when needed)."""
    if crypto.is_encrypted(path):
        if not passphrase:
            raise BackupError("النسخة مشفرة: أدخل كلمة السر")
        out = workdir / "decrypted.zip"
        crypto.decrypt_file(path, out, passphrase)
        return out
    return path


def read_manifest(zf: zipfile.ZipFile) -> dict:
    try:
        info = zf.getinfo("manifest.json")
    except KeyError as e:
        raise BackupError("ملف manifest.json غير موجود") from e
    if info.file_size > MAX_MANIFEST:
        raise BackupError("ملف manifest كبير بشكل غير طبيعي")
    try:
        m = json.loads(zf.read(info))
    except ValueError as e:
        raise BackupError("ملف manifest تالف") from e
    if not isinstance(m, dict) or m.get("app") != "AutoCare Pro" or not isinstance(m.get("files"), list):
        raise BackupError("ملف manifest غير صالح")
    if m.get("format_version") != FORMAT_VERSION:
        raise BackupError(f"إصدار صيغة النسخة غير مدعوم ({m.get('format_version')})")
    return m


def verify_archive(path: Path, passphrase: str | None = None, deep: bool = True, url=None) -> dict:
    """Full verification. `deep` additionally restores the dump into a temporary database and compares row counts."""
    url = pgtools.db_url(url)
    checks: list[dict] = []
    result = {"ok": False, "checks": checks, "manifest": None, "schema": None, "needs_upgrade": False}

    def check(name: str, ok: bool, detail: str = "") -> bool:
        checks.append({"name": name, "ok": ok, "detail": detail})
        return ok

    path = Path(path)
    workdir = Path(tempfile.mkdtemp(prefix="acverify-", dir=path.parent if path.parent.exists() else None))
    temp_db = None
    try:
        if not path.is_file():
            check("file_exists", False, "الملف غير موجود")
            return result
        encrypted = crypto.is_encrypted(path)
        try:
            zip_path = open_archive(path, passphrase, workdir)
            if encrypted:
                check("decrypt", True, "تم فك التشفير والتحقق من سلامة الملف المشفر")
        except BackupError as e:
            check("decrypt", False, str(e))
            return result
        try:
            zf = zipfile.ZipFile(zip_path)
        except (zipfile.BadZipFile, OSError) as e:
            check("archive_integrity", False, f"ملف zip غير صالح: {e}")
            return result
        with zf:
            bad = zf.testzip()
            if not check("archive_integrity", bad is None, f"ملف تالف داخل الأرشيف: {bad}" if bad else "الأرشيف سليم"):
                return result
            infos = zf.infolist()
            unsafe = [i.filename for i in infos if not i.filename.endswith("/") and
                      (not safe_member_name(i.filename) or _is_symlink(i))]
            if not check("safe_paths", not unsafe, f"مسارات غير آمنة: {unsafe[:3]}" if unsafe else "كل المسارات آمنة"):
                return result
            try:
                manifest = read_manifest(zf)
            except BackupError as e:
                check("manifest", False, str(e))
                return result
            check("manifest", True, f"أُنشئت {manifest.get('created_at')}")
            result["manifest"] = manifest
            listed = {f["path"]: f for f in manifest["files"] if isinstance(f, dict) and "path" in f}
            members = {i.filename: i for i in infos if not i.filename.endswith("/")}
            problems = []
            for name, f in listed.items():
                info = members.get(name)
                if not safe_member_name(name) or info is None:
                    problems.append(f"ناقص: {name}")
                    continue
                if info.file_size != f.get("size"):
                    problems.append(f"حجم مختلف: {name}")
                    continue
                h = hashlib.sha256()
                with zf.open(info) as fh:
                    for block in iter(lambda: fh.read(1024 * 1024), b""):
                        h.update(block)
                if h.hexdigest() != f.get("sha256"):
                    problems.append(f"checksum مختلف: {name}")
            extra = [n for n in members if n != "manifest.json" and n not in listed]
            if extra:
                problems.append(f"ملفات غير مدرجة: {extra[:3]}")
            if "database.dump" not in listed:
                problems.append("ملف قاعدة البيانات غير موجود")
            total = sum(i.file_size for i in infos)
            if total > sum(f.get("size", 0) for f in listed.values()) + MAX_MANIFEST + 1024:
                problems.append("حجم غير متوقع بعد فك الضغط")
            if not check("checksums", not problems, "; ".join(problems[:5]) if problems else f"{len(listed)} ملف مطابق للـ checksums (اكتمال المرفقات)"):
                return result
            compat = schema_compat(manifest.get("alembic_revision"))
            result["schema"] = compat
            result["needs_upgrade"] = compat == "older"
            if not check("schema", compat != "incompatible",
                         {"current": "نسخة قاعدة البيانات مطابقة للبرنامج", "older": "قاعدة بيانات أقدم: ستُرقّى عند الاستعادة",
                          "incompatible": "قاعدة البيانات أحدث من البرنامج أو غير معروفة، حدّث البرنامج أولاً"}[compat]):
                return result
            dump_path = workdir / "database.dump"
            with zf.open("database.dump") as src, open(dump_path, "wb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
        try:
            n = pgtools.pg_restore_list(url, dump_path)
            check("database_dump", n > 0, f"ملف قاعدة البيانات صالح ({n} عنصر)")
        except BackupError as e:
            check("database_dump", False, str(e))
            return result
        if deep:
            try:
                temp_db = pgtools.temp_db_name("autocare_verify")
                pgtools.create_database(url, temp_db)
                pgtools.pg_restore(url, dump_path, temp_db)
                eng = create_engine(pgtools.with_database(url, temp_db), poolclass=NullPool)
                with eng.connect() as c:
                    counts = {t: c.execute(text(f"select count(*) from {t}")).scalar() for t in COUNT_TABLES}
                    rev = c.execute(text("select version_num from alembic_version")).scalar()
                eng.dispose()
                mismatched = {t: (counts[t], manifest["row_counts"].get(t)) for t in COUNT_TABLES
                              if counts[t] != manifest["row_counts"].get(t)}
                ok = not mismatched and rev == manifest.get("alembic_revision")
                check("test_restore", ok, "تمت استعادة تجريبية ناجحة في قاعدة مؤقتة وتطابقت الأعداد" if ok
                      else f"اختلاف بعد الاستعادة التجريبية: {mismatched or rev}")
            except BackupError as e:
                check("test_restore", False, str(e))
            finally:
                if temp_db:
                    try:
                        pgtools.drop_database(url, temp_db)
                    except Exception:  # noqa: BLE001 - best effort cleanup
                        pass
        result["ok"] = all(c["ok"] for c in checks)
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
