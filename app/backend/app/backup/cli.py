"""Command-line recovery that works even when the web application cannot start.

    python -m app.backup.cli list
    python -m app.backup.cli create [--passphrase-env VAR] [--dir PATH]
    python -m app.backup.cli verify FILE [--passphrase-env VAR]
    python -m app.backup.cli import FILE            (copy an archive from USB/another disk into the backup folder, verified)
    python -m app.backup.cli restore FILE --yes [--passphrase-env VAR]

The passphrase is read from an environment variable (never from the command line, which other users can see).
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

from app.backup import archive, restore, service
from app.backup.pgtools import BackupError, db_url


def _pw(name: str | None) -> str | None:
    return os.environ.get(name) if name else None


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Arabic messages must not crash on a legacy Windows code page
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(prog="autocare-backup")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("create")
    c.add_argument("--passphrase-env")
    c.add_argument("--dir")
    v = sub.add_parser("verify")
    v.add_argument("file")
    v.add_argument("--passphrase-env")
    v.add_argument("--quick", action="store_true", help="skip the test restore")
    i = sub.add_parser("import")
    i.add_argument("file")
    i.add_argument("--passphrase-env")
    r = sub.add_parser("restore")
    r.add_argument("file")
    r.add_argument("--passphrase-env")
    r.add_argument("--yes", action="store_true", help="I understand current data will be replaced")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "list":
            from sqlalchemy import select
            from app.db import SessionLocal
            from app.models import BackupRecord
            with SessionLocal() as db:
                for rec in db.scalars(select(BackupRecord).order_by(BackupRecord.created_at.desc())):
                    print(f"{rec.status:10} {rec.trigger:11} {rec.name}")
            return 0
        if a.cmd == "create":
            rec = service.run_backup("manual", None, _pw(a.passphrase_env), dir_override=Path(a.dir) if a.dir else None)
            print(f"{rec.status}: {rec.name}" + (f" ({rec.error})" if rec.error else ""))
            return 0 if rec.status == "verified" else 1
        if a.cmd == "verify":
            res = archive.verify_archive(Path(a.file), _pw(a.passphrase_env), deep=not a.quick)
            for ch in res["checks"]:
                print(("OK   " if ch["ok"] else "FAIL ") + ch["name"] + ": " + ch["detail"])
            return 0 if res["ok"] else 1
        if a.cmd == "import":
            src = Path(a.file)
            res = archive.verify_archive(src, _pw(a.passphrase_env), deep=True)
            if not res["ok"]:
                print("الأرشيف لم يجتز الفحص:", [c for c in res["checks"] if not c["ok"]])
                return 1
            from app.db import SessionLocal
            with SessionLocal() as db:
                target = service.backup_dir(service.get_backup_settings(db))
            target.mkdir(parents=True, exist_ok=True)
            dest = target / src.name
            if dest.exists():
                print("يوجد ملف بنفس الاسم في مجلد النسخ الاحتياطي")
                return 1
            shutil.copy2(src, dest)
            print("تم الاستيراد:", dest, "| سُجل:", service.rescan(target))
            return 0
        if a.cmd == "restore":
            if not a.yes:
                print("سيتم استبدال البيانات الحالية. أعد الأمر مع --yes للتأكيد.")
                return 2
            out = restore.restore_backup(Path(a.file), _pw(a.passphrase_env))
            print("تمت الاستعادة. القاعدة السابقة محفوظة باسم:", out["previous_database"])
            return 0
    except BackupError as e:
        print("خطأ:", e)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
