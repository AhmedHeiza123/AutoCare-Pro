# AutoCare Pro — Administrator manual

## Roles and permissions
Permissions are enforced by the server on every request (hiding a button is cosmetic only).

| Role | Can |
|---|---|
| **Administrator** | everything, including users, security settings, backups/restores |
| **Workshop Manager** | all workshop operations, settings, technicians, overrides (delivery, reopen jobs), refunds, reports, audit log. **Not** users/backups |
| **Receptionist** | customers, vehicles, reception, jobs, parts, quotations & approvals, invoices & payments, delivery. No refunds/costs/settings |
| **Technician** | read customers/vehicles/jobs, update jobs, record parts and photos. Never sees part purchase costs or invoices |
| **Accountant** | invoices, payments, refunds, credit notes, expenses, suppliers, financial reports, part costs. Cannot change jobs |

Users: **المستخدمين** (create, change role, disable, reset password — a reset/disable signs the person out everywhere).
Accounts are never deleted (history keeps who did what). Passwords: Argon2id, minimum 8 characters, lock-out after repeated
failures (configurable in الإعدادات → الأمان: session length, attempts, lock duration).

## Languages
The interface is available in Arabic and English (button in the top bar). **Settings → General → Default system language** is what new devices start with. Typed data is not auto-translated. See `docs/I18N.md`.

## Settings (الإعدادات)
Workshop name/address/phone/tax number/logo (printed on every document), currency, default tax rate (**0 = no tax; tax is never
assumed**), invoice/credit-note prefix and number width, payment methods, default labour rate, default part/labour warranty,
working hours, theme. Every change is audited with before/after values.

## Audit log (سجل العمليات)
Append-only, enforced inside the database (UPDATE/DELETE are rejected by a trigger). Records logins and failures, customer/vehicle/
job/invoice/payment changes, permission changes, backups, restores, report exports, overrides — with user, time, IP, before/after
and the reason where required. Filter by action prefix (e.g. `invoice.`), user, dates.

## Data rules worth knowing
* Customers, vehicles, jobs, invoices, payments are **never hard-deleted**; use deactivate / cancel / credit note / refund.
* Issued invoices are immutable (API **and** database triggers). Correct with a credit note, or cancel (only when nothing is held).
* A job delivers only when: work finished, parts installed, quality check passed, invoice issued and fully paid. Managers can override
  **with a written reason**; the override is part of the delivery report and the audit log.
* One live invoice per job; payments/invoices/deposits carry idempotency keys and database row locks, so double clicks and
  simultaneous cashiers cannot double-charge or overpay.
* Concurrent edits: job cards use optimistic concurrency (a stale edit is refused with a clear message).

## Backups
See **docs/RECOVERY.md** (scheduling, retention, encryption, verification with a real test restore, guided restore, CLI recovery).
Daily 02:00 is the default. Put the backup folder on a **different device**. Keep the encryption passphrase on paper elsewhere.

## Network modes
* **Single computer:** default (`AUTOCARE_HOST=127.0.0.1`). Open `http://localhost:8000`.
* **Local network:** install with `-LanMode` (binds `0.0.0.0`, opens the firewall for the **private** profile only). Other devices use
  `http://<pc-ip>:8000`. Add `-Https` for a self-signed certificate (browsers warn once; install the `.crt` on devices to remove it).
  Give the server PC a fixed IP/reservation on the router. Do **not** expose the port to the internet.

## Routine checklist
Daily: glance at the Backup screen (last success is green and recent). Weekly: copy the newest backup to a USB drive kept off-site.
Monthly: run **فحص واستعادة تجريبية** on an old backup; review the audit log for overrides; review users.

## API & integration
`docs/API.md` lists every endpoint with its required permission. The interactive Swagger page is deliberately disabled (it loads
scripts from the internet, which breaks the offline requirement).
