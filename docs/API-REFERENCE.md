# API reference and endpoint inventory

This source-derived inventory contains **118 domain API routes**, plus the explicit health route. It was generated from the supplied Python router decorators and reviewed for permission aliases and checks inside handlers. It is an endpoint index, not a complete request/response schema or a tested OpenAPI contract.

## Base URL and conventions

- Direct Python startup: `http://127.0.0.1:8000` by default.
- Complete Windows installer: normally `http://localhost:8080`; setup can select another port.
- Domain endpoints use `/api`. `GET /health` is public and returns a status/version after a database connectivity query.
- The frontend uses the same origin as the API. Browser clients authenticate with the session cookie.
- Login returns CSRF information; authenticated POST/PUT/PATCH/DELETE requests must send the matching `X-CSRF-Token` header.
- Selected invoice/payment creation routes accept `Idempotency-Key`; consult their function signatures before integrating. Reuse one key for one intended operation, not across unrelated actions.
- Permissions shown below describe entry checks and known dynamic checks. Some handlers impose additional business rules, override permissions and field visibility restrictions.
- `GET /api/auth/setup-needed`, `POST /api/auth/setup`, `POST /api/auth/login` and `GET /api/restore/status` are intentionally unauthenticated. Setup refuses to create another first administrator after a user exists.
- Swagger, ReDoc and the OpenAPI URL are disabled. The generator referenced by an old source comment was not included.

## Authentication flow

1. Check `GET /api/auth/setup-needed` on a fresh local installation.
2. If needed, `POST /api/auth/setup` creates the first administrator. Required input: username, full name and password. Optional setup input includes workshop details, currency, default tax rate, backup directory and language.
3. `POST /api/auth/login` accepts username/password, sets the HttpOnly session cookie and returns the user/CSRF information.
4. Preserve the cookie and supply the CSRF token on authenticated mutations. `GET /api/auth/me` returns the current identity and CSRF information.
5. `POST /api/auth/logout` deletes the session and clears the cookie.

Do not put passwords, cookie values or CSRF tokens in example repositories, screenshots, logs or issue reports.

## Representative input contracts

| Route | Important input fields | Source/notes |
|---|---|---|
| `POST /api/auth/setup` | `username`, `full_name`, `password`; optional `workshop`, `currency`, `default_tax_rate`, `backup_dir`, `language` | `SetupIn` in auth module; workshop object is separately validated |
| `POST /api/auth/login` | `username`, `password` | `LoginIn`; login failures and lockouts can return non-success statuses |
| `POST /api/jobs/{job_id}/quality-check` | `result`, `repairs_verified`, `parts_verified`, `road_test_ok`, optional `notes`/`override_reason` | `QCIn`; passed results require the checklist |
| `POST /api/jobs/{job_id}/deliver` | `final_mileage`, `ack_name`, optional `final_condition`, `ack_note`, `override_reason` | `DeliverIn`; readiness checks and override rules also apply |
| `POST /api/attachments` | Multipart `file`, `owner_type`, `owner_id`; optional `kind`, `point`, `note` | Generated filenames and signature checks; 10 MiB image / 20 MiB PDF limits |
| `POST /api/backups` | Optional `passphrase` | Administrator-only, asynchronous operation with a returned record ID |
| `POST /api/restore` | `id`, optional `passphrase`, `confirm`, `admin_password` | Confirmation must equal `RESTORE`; destructive operational action, not a public integration example |

Validate the complete Pydantic model and handler before writing an integration. The tables do not enumerate every field constraint, payload or response shape.

## Error conventions

Application errors generally return JSON containing `error` and `message`. Codes/statuses visible in handlers include authentication failure (401), permission/CSRF denial (403), missing record (404), conflicting/stale changes (409), lockout (423), validation/business errors (422), rate limiting (429) and maintenance mode (503). Unexpected exceptions use a generic 500 response. FastAPI/Pydantic validation errors may use FastAPI's separate `detail` shape; do not assume every error has the application shape.

## Endpoint index

Source locations below are relative to the original `AutoCare-Pro-Setup/` root. Permissions are a navigation aid, not an authorization guarantee.

### attachments

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| POST | `/api/attachments` | authenticated + owner-type permission | `app/backend/app/api/attachments.py` |
| GET | `/api/attachments` | authenticated + owner-type permission | `app/backend/app/api/attachments.py` |
| GET | `/api/attachments/{att_id}/file` | authenticated + owner-type permission | `app/backend/app/api/attachments.py` |
| POST | `/api/attachments/{att_id}/remove` | authenticated + owner-type permission | `app/backend/app/api/attachments.py` |

### audit_view

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/audit` | audit.read | `app/backend/app/api/audit_view.py` |

### auth

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/auth/setup-needed` | public | `app/backend/app/api/auth.py` |
| POST | `/api/auth/setup` | loopback only, before first user exists | `app/backend/app/api/auth.py` |
| POST | `/api/auth/login` | public | `app/backend/app/api/auth.py` |
| POST | `/api/auth/logout` | authenticated | `app/backend/app/api/auth.py` |
| GET | `/api/auth/me` | authenticated | `app/backend/app/api/auth.py` |
| GET | `/api/users` | users.manage | `app/backend/app/api/auth.py` |
| POST | `/api/users` | users.manage | `app/backend/app/api/auth.py` |
| PATCH | `/api/users/{user_id}` | users.manage | `app/backend/app/api/auth.py` |
| POST | `/api/auth/change-password` | authenticated | `app/backend/app/api/auth.py` |
| POST | `/api/users/{user_id}/reset-password` | users.manage | `app/backend/app/api/auth.py` |
| GET | `/api/roles` | users.manage | `app/backend/app/api/auth.py` |

### backup

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/backups` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/backups` | backup.manage | `app/backend/app/api/backup.py` |
| GET | `/api/backups/{rid}` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/backups/{rid}/verify` | backup.manage | `app/backend/app/api/backup.py` |
| GET | `/api/backups/{rid}/download` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/backups/{rid}/delete` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/backups/rescan` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/backups/recovery-secret` | backup.manage | `app/backend/app/api/backup.py` |
| PUT | `/api/backup-settings` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/restore/preview` | backup.manage | `app/backend/app/api/backup.py` |
| POST | `/api/restore` | backup.manage | `app/backend/app/api/backup.py` |
| GET | `/api/restore/status` | public | `app/backend/app/api/backup.py` |

### billing

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| POST | `/api/jobs/{job_id}/invoices` | billing.write | `app/backend/app/api/billing.py` |
| GET | `/api/invoices` | billing.read | `app/backend/app/api/billing.py` |
| GET | `/api/jobs/{job_id}/invoices` | billing.read | `app/backend/app/api/billing.py` |
| GET | `/api/invoices/verify` | billing.read | `app/backend/app/api/billing.py` |
| GET | `/api/invoices/{invoice_id}/document` | billing.read | `app/backend/app/api/billing.py` |
| GET | `/api/invoices/{invoice_id}/pdf` | billing.read | `app/backend/app/api/billing.py` |
| GET | `/api/invoices/{invoice_id}` | billing.read | `app/backend/app/api/billing.py` |
| PATCH | `/api/invoices/{invoice_id}` | billing.write | `app/backend/app/api/billing.py` |
| POST | `/api/invoices/{invoice_id}/items` | billing.write | `app/backend/app/api/billing.py` |
| DELETE | `/api/invoices/{invoice_id}/items/{item_id}` | billing.write | `app/backend/app/api/billing.py` |
| DELETE | `/api/invoices/{invoice_id}` | billing.write | `app/backend/app/api/billing.py` |
| POST | `/api/invoices/{invoice_id}/issue` | billing.write | `app/backend/app/api/billing.py` |
| POST | `/api/invoices/{invoice_id}/cancel` | billing.refund | `app/backend/app/api/billing.py` |
| POST | `/api/invoices/{invoice_id}/payments` | billing.write | `app/backend/app/api/billing.py` |
| POST | `/api/jobs/{job_id}/deposits` | billing.write | `app/backend/app/api/billing.py` |
| GET | `/api/jobs/{job_id}/deposits` | billing.read | `app/backend/app/api/billing.py` |
| POST | `/api/payments/{payment_id}/refunds` | billing.refund | `app/backend/app/api/billing.py` |
| POST | `/api/invoices/{invoice_id}/credit-notes` | billing.refund | `app/backend/app/api/billing.py` |
| POST | `/api/credit-notes/{credit_id}/cancel` | billing.refund | `app/backend/app/api/billing.py` |

### customers

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/customers/{customer_id}` | customers.read | `app/backend/app/api/customers.py` |
| PATCH | `/api/customers/{customer_id}` | customers.write | `app/backend/app/api/customers.py` |

### delivery

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/jobs/{job_id}/delivery-readiness` | visits.read | `app/backend/app/api/delivery.py` |
| POST | `/api/jobs/{job_id}/quality-check` | qc.write | `app/backend/app/api/delivery.py` |
| POST | `/api/jobs/{job_id}/deliver` | delivery.write | `app/backend/app/api/delivery.py` |
| GET | `/api/jobs/{job_id}/delivery-report` | visits.read | `app/backend/app/api/delivery.py` |

### finance

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/expense-categories` | expenses.read | `app/backend/app/api/finance.py` |
| POST | `/api/expense-categories` | expenses.write | `app/backend/app/api/finance.py` |
| POST | `/api/expenses` | expenses.write | `app/backend/app/api/finance.py` |
| GET | `/api/expenses` | expenses.read | `app/backend/app/api/finance.py` |
| POST | `/api/expenses/{expense_id}/void` | expenses.write | `app/backend/app/api/finance.py` |
| GET | `/api/reports/financial-summary` | reports.financial | `app/backend/app/api/finance.py` |

### jobs

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/templates` | visits.read | `app/backend/app/api/jobs.py` |
| GET | `/api/technicians` | visits.read | `app/backend/app/api/jobs.py` |
| POST | `/api/technicians` | technicians.manage | `app/backend/app/api/jobs.py` |
| PATCH | `/api/technicians/{tech_id}` | technicians.manage | `app/backend/app/api/jobs.py` |
| POST | `/api/reception` | visits.write | `app/backend/app/api/jobs.py` |
| GET | `/api/jobs/{job_id}/receipt` | visits.read | `app/backend/app/api/jobs.py` |
| GET | `/api/jobs/{job_id}` | visits.read | `app/backend/app/api/jobs.py` |
| POST | `/api/jobs/{job_id}/status` | visits.write | `app/backend/app/api/jobs.py` |
| POST | `/api/jobs/{job_id}/assign` | visits.write | `app/backend/app/api/jobs.py` |
| POST | `/api/jobs/{job_id}/unassign` | visits.write | `app/backend/app/api/jobs.py` |
| POST | `/api/jobs/{job_id}/operations` | visits.write | `app/backend/app/api/jobs.py` |
| PATCH | `/api/operations/{op_id}` | visits.write | `app/backend/app/api/jobs.py` |
| POST | `/api/jobs/{job_id}/inspections` | visits.write | `app/backend/app/api/jobs.py` |
| GET | `/api/board` | visits.read | `app/backend/app/api/jobs.py` |

### parts

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/suppliers` | visits.read | `app/backend/app/api/parts.py` |
| POST | `/api/suppliers` | suppliers.write | `app/backend/app/api/parts.py` |
| PATCH | `/api/suppliers/{sid}` | suppliers.write | `app/backend/app/api/parts.py` |
| POST | `/api/jobs/{job_id}/parts` | parts.write | `app/backend/app/api/parts.py` |
| GET | `/api/jobs/{job_id}/parts` | visits.read | `app/backend/app/api/parts.py` |
| GET | `/api/parts` | visits.read | `app/backend/app/api/parts.py` |
| PATCH | `/api/parts/{part_id}` | parts.write | `app/backend/app/api/parts.py` |
| POST | `/api/parts/{part_id}/status` | parts.write | `app/backend/app/api/parts.py` |
| POST | `/api/parts/{part_id}/return` | parts.write | `app/backend/app/api/parts.py` |
| GET | `/api/suppliers/{sid}/purchases` | visits.read | `app/backend/app/api/parts.py` |

### quotes

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| POST | `/api/jobs/{job_id}/quotations` | quotes.write | `app/backend/app/api/quotes.py` |
| GET | `/api/jobs/{job_id}/quotations` | visits.read | `app/backend/app/api/quotes.py` |
| GET | `/api/quotations/{qid}` | visits.read | `app/backend/app/api/quotes.py` |
| PATCH | `/api/quotations/{qid}` | quotes.write | `app/backend/app/api/quotes.py` |
| POST | `/api/quotations/{qid}/items` | quotes.write | `app/backend/app/api/quotes.py` |
| DELETE | `/api/quotations/{qid}/items/{item_id}` | quotes.write | `app/backend/app/api/quotes.py` |
| POST | `/api/quotations/{qid}/send` | quotes.write | `app/backend/app/api/quotes.py` |
| POST | `/api/quotations/{qid}/approvals` | quotes.approve | `app/backend/app/api/quotes.py` |

### reports

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/reports` | authenticated + report-specific permission | `app/backend/app/api/reports.py` |
| GET | `/api/reports/{name}` | authenticated + report-specific permission | `app/backend/app/api/reports.py` |
| GET | `/api/reports/{name}/export` | authenticated + report-specific permission | `app/backend/app/api/reports.py` |

### search

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/search` | authenticated | `app/backend/app/api/search.py` |

### settings_api

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/settings` | authenticated | `app/backend/app/api/settings_api.py` |
| GET | `/api/settings/security` | users.manage | `app/backend/app/api/settings_api.py` |
| PUT | `/api/settings/{section}` | authenticated + section permission | `app/backend/app/api/settings_api.py` |

### vehicles

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| POST | `/api/vehicles` | vehicles.write | `app/backend/app/api/vehicles.py` |
| GET | `/api/vehicles` | vehicles.read | `app/backend/app/api/vehicles.py` |
| GET | `/api/vehicles/{vehicle_id}` | vehicles.read | `app/backend/app/api/vehicles.py` |
| PATCH | `/api/vehicles/{vehicle_id}` | vehicles.write | `app/backend/app/api/vehicles.py` |
| POST | `/api/vehicles/{vehicle_id}/change-owner` | vehicles.write | `app/backend/app/api/vehicles.py` |
| POST | `/api/visits` | visits.write | `app/backend/app/api/vehicles.py` |
| GET | `/api/visits/{visit_id}` | visits.read | `app/backend/app/api/vehicles.py` |
| PATCH | `/api/visits/{visit_id}` | visits.write | `app/backend/app/api/vehicles.py` |
| GET | `/api/vehicles/{vehicle_id}/history` | visits.read | `app/backend/app/api/vehicles.py` |

### vehicle_health

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| GET | `/api/vehicles/{vehicle_id}/health` | visits.read | `app/backend/app/api/vehicle_health.py` |

### warranty

| Method | Path | Access / permission | Source file |
|---|---|---|---|
| POST | `/api/jobs/{job_id}/warranties` | visits.write | `app/backend/app/api/warranty.py` |
| GET | `/api/jobs/{job_id}/warranties` | visits.read | `app/backend/app/api/warranty.py` |
| GET | `/api/vehicles/{vehicle_id}/warranties` | visits.read | `app/backend/app/api/warranty.py` |
| GET | `/api/warranties` | visits.read | `app/backend/app/api/warranty.py` |
| POST | `/api/warranties/{wid}/void` | warranties.decide | `app/backend/app/api/warranty.py` |
| POST | `/api/warranties/{wid}/claims` | visits.write | `app/backend/app/api/warranty.py` |
| POST | `/api/claims/{cid}/decide` | warranties.decide | `app/backend/app/api/warranty.py` |
| POST | `/api/vehicles/{vehicle_id}/reminders` | visits.write | `app/backend/app/api/warranty.py` |
| GET | `/api/reminders` | visits.read | `app/backend/app/api/warranty.py` |
| POST | `/api/reminders/{rid}/{action}` | visits.write | `app/backend/app/api/warranty.py` |

The health route and SPA static/catch-all routes are defined in `app/backend/app/main.py`, outside the domain-router count. Route payloads, response formats and runtime status codes were not exercised.

Final security pass: initial setup checks the actual loopback client; public restore status omits raw detail/error fields. No new endpoint was introduced. Source-line offsets from earlier drafts are not retained after remediation.
