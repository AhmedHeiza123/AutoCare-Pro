from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import inventory, inventory_jobs, vehicle_health, reports, search, settings_api, attachments, audit_view, auth, backup, billing, customers, delivery, finance, jobs, parts, quotes, vehicles, warranty
from app.backup import service as backup_service
from app.core import maintenance
from app.core.errors import install_handlers
from app.db import SessionLocal, engine
from app.version import APP_VERSION


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        auth.seed_roles(db)
        finance.seed_expense_categories(db)
        db.commit()
    backup_service.recover_interrupted()
    backup_service.start_scheduler()
    yield
    backup_service.stop_scheduler()


# No /docs or /redoc or /openapi.json: the bundled UIs load scripts from a CDN, which breaks the offline requirement
# (and the API schema is not exposed to anonymous visitors).
app = FastAPI(title="AutoCare Pro", version=APP_VERSION, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
install_handlers(app)
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(vehicles.router)
app.include_router(jobs.router)
app.include_router(parts.router)
app.include_router(quotes.router)
app.include_router(billing.router)
app.include_router(finance.router)
app.include_router(delivery.router)
app.include_router(warranty.router)
app.include_router(backup.router)
app.include_router(attachments.router)
app.include_router(audit_view.router)
app.include_router(settings_api.router)
app.include_router(reports.router)
app.include_router(search.router)
app.include_router(vehicle_health.router)
app.include_router(inventory.router)
app.include_router(inventory_jobs.router)


@app.middleware("http")
async def maintenance_mode(request, call_next):
    """While a restore runs, refuse API calls (the SPA shell and /health stay reachable to show a notice)."""
    path = request.url.path
    if maintenance.is_active() and path.startswith("/api/") and path != "/api/restore/status":
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "maintenance", "message": "النظام تحت الصيانة (استعادة نسخة احتياطية)، حاول بعد قليل"},
                            status_code=503)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:")
    return resp


@app.get("/health")
def health():
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return {"status": "ok", "version": APP_VERSION}


# ---- serve the built single-page app (same origin => cookies/CSRF just work) ----
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
NO_CACHE = {"Cache-Control": "no-cache"}  # always revalidate the HTML shell so an update is picked up at once (hashed /assets use ETags)
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST in f.parents:
            return FileResponse(f, headers=NO_CACHE)
        return FileResponse(DIST / "index.html", headers=NO_CACHE)
