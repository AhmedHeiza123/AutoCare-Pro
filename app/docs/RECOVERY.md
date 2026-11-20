# AutoCare Pro — Backup & Disaster Recovery Guide (administrator)

> Status: the procedures below for **restore, verification, encryption, retention and the CLI** are covered by automated
> tests against a real PostgreSQL (see `backend/tests/test_backup.py`). The Windows-reinstall and new-computer steps are
> documented procedures that have **not yet been rehearsed on a clean Windows machine**.

## What a backup contains
One archive `AutoCarePro_Backup_YYYY-MM-DD_HHMMSS.zip` (or `.zip.enc` when encrypted):
`database.dump` (consistent PostgreSQL snapshot: customers, vehicles, history, jobs, parts, invoices, payments, expenses,
users, permissions, audit log, settings), `files/` (attachments and generated documents), `config.json` (non-secret
settings), `manifest.json` (versions, row counts, SHA-256 of every file).
**Not inside:** your `.env` file (database password, secret key). Keep a copy of `.env` somewhere safe separately.

A backup is only marked ✔ *verified* after: archive integrity, safe paths, manifest, checksums, schema compatibility,
`pg_restore --list`, **and a test restore into a temporary database whose row counts must match** (the temporary
database is then dropped). A checksum alone is not accepted as proof.

## Keep copies on a different device
Settings → النسخ الاحتياطي → النسخ التلقائي → مكان الحفظ: point it at a USB drive / second disk / network share.
At minimum copy the newest archive to a USB stick weekly. A backup that lives only on the same disk dies with it.

## Encryption — read this
Encrypted backups use AES-256-GCM with a key derived from your passphrase (scrypt). The passphrase is **never stored
inside the archive**. **Without the passphrase an encrypted backup cannot be recovered by anyone, including us.**
Use "توليد كلمة سر قوية", write it on paper, store it away from the computer.
Scheduled encrypted backups read the passphrase from the `AUTOCARE_BACKUP_PASSPHRASE` environment variable or the file
`storage/secrets/backup.pass` (restrict that file to the service account).

## Restore from the screen (system is working)
1. النسخ الاحتياطي → استعادة نسخة → pick the backup → **فحص النسخة** (full verification).
2. Type `RESTORE` and your admin password.
3. The system makes a **safety backup of the current state**, enters maintenance mode, restores into a *new* database,
   migrates it if it is from an older version, checks the counts, then swaps it in. Everyone is logged out.
4. The previous database stays as `<name>_old_<timestamp>` and the previous attachment folders as
   `attachments.pre-restore-<timestamp>` until you remove them. If any step fails the system rolls back automatically.
A backup made by a **newer** program version is refused (no silent downgrade): update the program first.

## When the application will not start (command line)
Open PowerShell in the `backend` folder (PostgreSQL service must be running):
```bash
python -m app.backup.cli list
python -m app.backup.cli verify D:\Backups\AutoCarePro_Backup_2026-10-19_020000.zip
python -m app.backup.cli import  E:\AutoCarePro_Backup_....zip        # copy from USB into the managed folder, verified
$env:BK_PASS = "your passphrase"                                       # only for encrypted archives
python -m app.backup.cli restore D:\Backups\AutoCarePro_Backup_....zip --yes --passphrase-env BK_PASS
```
`restore` works even if the live database is missing or damaged: it builds a fresh database and swaps it in.

## Scenarios
| Situation | What to do |
|---|---|
| **Computer failure** | Install the program on a new PC (see installation guide), restore `.env`, put the newest archive (from USB) anywhere, run `cli import` then `cli restore --yes`. |
| **Database corruption** | `cli restore` the newest *verified* archive. The damaged database is kept as `*_old_*` for forensics. |
| **Accidental deletion** | Restore the last good backup into place, or ask for a partial recovery from the `*_old_*`/safety database. Customer/vehicle/financial records are never hard-deleted by the program; corrections are audited. |
| **Windows reinstall** | Reinstall PostgreSQL and the program, restore `.env`, `cli import` the archive, `cli restore --yes`. |
| **Moving to a new computer** | Make a backup, copy the archive + `.env` to the new PC, install, `cli import`, `cli restore --yes`, update the backup folder in the settings. |
| **Restoring from USB** | Plug the drive, `cli verify <file>` then `cli import <file>` then restore from the screen or the CLI. |
| **Failed application upgrade** | Before upgrading always create a backup. If the upgrade breaks things: reinstall the previous program version, then restore that backup. |
| **Interrupted backup** | Nothing to do: partial files are removed, earlier backups are untouched, the attempt is shown as failed, and the scheduler retries after 30 minutes. |

## Housekeeping
Retention (default 7 daily / 4 weekly / 12 monthly) never deletes the last valid backup. Pre-restore safety backups are
kept 90 days. Old `*_old_*` databases can be dropped once you are sure the restore is good.
