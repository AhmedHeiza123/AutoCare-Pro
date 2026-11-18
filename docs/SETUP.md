# Local setup

Use a separate source folder and empty development database. This source candidate excludes the original installer/runtimes and has not replaced the installed application.

## Backend

Use Python 3.12 and PostgreSQL, with a dedicated role owning `autocare_recovery_dev`. Recovery may need database-creation privileges; review those separately from routine application access.

From the root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/backend/requirements.txt
Copy-Item app/backend/.env.example app/backend/.env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `.env` privately: replace database placeholders and the rejected `CHANGE_ME` secret. Keep host `127.0.0.1`, development port `18080` and scheduler disabled for isolated work. URL-encode database credentials; do not copy live data/configuration.

```powershell
Set-Location app/backend
..\..\.venv\Scripts\python.exe -m alembic upgrade head
..\..\.venv\Scripts\python.exe -m app.server
```

First-admin setup requires a loopback connection. Do not proxy/expose an uninitialized installation. These describe fresh-environment steps; the smoke test reused installed packages. Direct requirements are pinned, but a complete resolved backend lockfile is not supplied.

## Frontend

Use Node 24.11+ and pnpm 11.25.0. From `app/frontend`:

```powershell
pnpm install --frozen-lockfile --ignore-scripts
pnpm test
pnpm build
$env:AUTOCARE_API_TARGET = 'http://127.0.0.1:18080'
pnpm dev
```

Dev uses `127.0.0.1:5173`; `pnpm preview` uses `127.0.0.1:4173`. Both require an explicit trusted backend origin. A localhost origin is not proof that a database is disposable. FastAPI can serve the built frontend itself. Core UI assets are local; dependency installation may need registry access.

## Tests and recovery tooling

```powershell
# From app/frontend
pnpm test
pnpm exec playwright install chromium
pnpm test:browser

# From the repository root
python -m unittest discover -s app/backend/tests -v
```

Browser checks build fresh output and start their own fixture API. `AUTOCARE_BROWSER_EXECUTABLE` can select compatible installed Chrome. Raw reports/images are generated locally and excluded from commits.

`pnpm recover` is blocked in this reviewed candidate because it would overwrite security patches. The baseline remains for provenance; any new recovery work must reapply/retest those patches.

The demo generator requires `AUTOCARE_DEMO_PASSWORD` and does not print it. See `app/docs/DEMO-SETUP.md`. Its TestClient now supplies a loopback client address. Full demo seeding remains untested and needs additional `httpx`, absent from production requirements.

Before LAN use, follow [SECURITY.md](../SECURITY.md), configure HTTPS and protect recovery artifacts. These source-preparation steps register no services and change no firewall rules.
