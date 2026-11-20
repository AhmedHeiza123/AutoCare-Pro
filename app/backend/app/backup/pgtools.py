"""Thin, safe wrappers around pg_dump / pg_restore and database administration."""
import glob
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class BackupError(Exception):
    """A backup/restore failure with a message that is safe to show to the administrator."""


def find_binary(name: str) -> str:
    exe = name + (".exe" if os.name == "nt" else "")
    s = get_settings()
    cands: list[Path] = []
    if s.pg_bin_dir:
        cands.append(Path(s.pg_bin_dir) / exe)
    found = shutil.which(name)
    if found:
        cands.append(Path(found))
    for pattern in (r"C:\Program Files\PostgreSQL\*\bin", r"C:\Users\*\dev-tools\pgsql\bin", "/usr/lib/postgresql/*/bin"):
        for d in sorted(glob.glob(pattern), reverse=True):
            cands.append(Path(d) / exe)
    for c in cands:
        if c.exists():
            return str(c)
    raise BackupError(f"لم يتم العثور على أداة PostgreSQL ({name}). حدد AUTOCARE_PG_BIN_DIR في ملف الإعدادات.")


def db_url(url: str | None = None) -> URL:
    return make_url(url or get_settings().database_url)


def with_database(url: URL, database: str) -> URL:
    return url.set(database=database)


def _env(url: URL) -> dict:
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password  # passed via environment, never on the command line or in logs
    env["PGCLIENTENCODING"] = "UTF8"
    return env


def _conn_args(url: URL) -> list[str]:
    args = ["-h", url.host or "127.0.0.1", "-p", str(url.port or 5432)]
    if url.username:
        args += ["-U", url.username]
    return args


def _scrub(msg: str, url: URL) -> str:
    return msg.replace(url.password, "***") if url.password else msg


def run_tool(binary: str, args: list[str], url: URL, timeout: int = 3600) -> subprocess.CompletedProcess:
    cmd = [find_binary(binary), *_conn_args(url), *args]
    try:
        proc = subprocess.run(cmd, env=_env(url), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise BackupError(f"انتهت مهلة {binary}") from e
    if proc.returncode != 0:
        err = _scrub(proc.stderr.decode("utf-8", "replace").strip()[-600:], url)
        raise BackupError(f"{binary} فشل: {err}")
    return proc


def pg_dump(url: URL, out_file: Path, snapshot: str | None, exclude_data: list[str]) -> None:
    args = ["-Fc", "--no-owner", "--no-privileges", "-f", str(out_file), "-d", url.database]
    if snapshot:
        args += ["--snapshot", snapshot]
    for t in exclude_data:
        args += ["--exclude-table-data", t]
    run_tool("pg_dump", args, url)


def pg_restore(url: URL, dump_file: Path, database: str) -> None:
    run_tool("pg_restore", ["--no-owner", "--no-privileges", "--exit-on-error", "-d", database, str(dump_file)], url)


def pg_restore_list(url: URL, dump_file: Path) -> int:
    proc = run_tool("pg_restore", ["--list", str(dump_file)], url, timeout=300)
    return len([ln for ln in proc.stdout.decode("utf-8", "replace").splitlines() if ln and not ln.startswith(";")])


# ---- administration (connects to the maintenance database) -------------------------
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def _ident(name: str) -> str:
    if not _IDENT.match(name):
        raise BackupError("اسم قاعدة بيانات غير صالح")
    return name


def admin_engine(url: URL):
    return create_engine(with_database(url, "postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool)


def database_exists(url: URL, name: str) -> bool:
    eng = admin_engine(url)
    try:
        with eng.connect() as c:
            return c.execute(text("select 1 from pg_database where datname = :n"), {"n": name}).scalar() is not None
    finally:
        eng.dispose()


def create_database(url: URL, name: str) -> None:
    eng = admin_engine(url)
    try:
        with eng.connect() as c:
            c.execute(text(f"CREATE DATABASE {_ident(name)} ENCODING 'UTF8' TEMPLATE template0"))
    finally:
        eng.dispose()


def drop_database(url: URL, name: str) -> None:
    eng = admin_engine(url)
    try:
        with eng.connect() as c:
            c.execute(text("select pg_terminate_backend(pid) from pg_stat_activity where datname = :n and pid <> pg_backend_pid()"), {"n": name})
            c.execute(text(f"DROP DATABASE IF EXISTS {_ident(name)}"))
    finally:
        eng.dispose()


def terminate_connections(url: URL, name: str) -> None:
    eng = admin_engine(url)
    try:
        with eng.connect() as c:
            c.execute(text("select pg_terminate_backend(pid) from pg_stat_activity where datname = :n and pid <> pg_backend_pid()"), {"n": name})
    finally:
        eng.dispose()


def rename_database(url: URL, old: str, new: str, attempts: int = 10) -> None:
    """Rename a database. A client may reconnect between terminating sessions and renaming, so retry on 'in use'."""
    import time
    last: Exception | None = None
    for _ in range(attempts):
        terminate_connections(url, old)
        eng = admin_engine(url)
        try:
            with eng.connect() as c:
                c.execute(text(f"ALTER DATABASE {_ident(old)} RENAME TO {_ident(new)}"))
            return
        except Exception as e:  # noqa: BLE001 - only the "being accessed by other users" case is retried
            last = e
            if "being accessed by other users" not in str(e):
                raise
            time.sleep(0.5)
        finally:
            eng.dispose()
    raise BackupError(f"تعذر إعادة تسمية قاعدة البيانات لأن جلسات أخرى ما زالت متصلة: {last}")


def temp_db_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def server_version(url: URL) -> str:
    eng = create_engine(url, poolclass=NullPool)
    try:
        with eng.connect() as c:
            return c.execute(text("show server_version")).scalar()
    finally:
        eng.dispose()
