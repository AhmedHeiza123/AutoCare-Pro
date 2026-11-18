"""Global search across customers, vehicles, job cards, invoices and parts (Arabic-aware, partial matches)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import current_user
from app.core.text import compact, digits, normalize
from app.db import get_db
from app.models import Customer, Invoice, PartPurchase, Vehicle, VehicleVisit
from app.models.auth import User

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=100), limit: int = Query(8, ge=1, le=25),
           user: User = Depends(current_user), db: DbSession = Depends(get_db, scope="function")):
    """Only the groups the caller may read are returned."""
    perms = user.permissions
    nq, cq, dq = normalize(q), compact(q), digits(q)
    out: dict[str, list] = {"customers": [], "vehicles": [], "jobs": [], "invoices": [], "parts": []}

    if "customers.read" in perms:
        conds = [Customer.search_text.contains(nq)]
        if dq:
            conds.append(Customer.mobile_compact.contains(dq))
        out["customers"] = [{"id": str(c.id), "name": c.full_name, "mobile": c.mobile, "customer_no": c.customer_no}
                            for c in db.scalars(select(Customer).where(or_(*conds)).order_by(Customer.full_name).limit(limit))]

    if "vehicles.read" in perms:
        conds = [Vehicle.search_text.contains(nq)]
        if cq:
            conds.append(Vehicle.plate_compact.contains(cq))
            conds.append(Vehicle.vin.ilike(f"%{q.strip()}%"))
        out["vehicles"] = [{"id": str(v.id), "plate": v.plate, "make": v.make, "model": v.model, "vin": v.vin}
                           for v in db.scalars(select(Vehicle).where(or_(*conds)).order_by(Vehicle.created_at.desc()).limit(limit))]

    if "visits.read" in perms:
        conds = []
        raw = q.strip().upper().removeprefix("JOB").lstrip("- #")
        if raw.isdigit():
            conds.append(VehicleVisit.visit_no == int(raw))
        if cq:
            conds.append(VehicleVisit.plate_at_visit.ilike(f"%{q.strip()}%"))
        if conds:
            rows = db.execute(select(VehicleVisit, Vehicle).join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id)
                              .where(or_(*conds)).order_by(VehicleVisit.arrival_at.desc()).limit(limit)).all()
            out["jobs"] = [{"id": str(j.id), "job_no": j.visit_no, "status": j.status, "plate": v.plate, "vehicle": f"{v.make} {v.model}"}
                           for j, v in rows]
        like = f"%{q.strip()}%"
        parts = db.execute(select(PartPurchase, VehicleVisit.visit_no).join(VehicleVisit, VehicleVisit.id == PartPurchase.visit_id)
                           .where(or_(PartPurchase.part_number.ilike(like), PartPurchase.part_name.ilike(like)))
                           .order_by(PartPurchase.id.desc()).limit(limit)).all()
        out["parts"] = [{"id": p.id, "visit_id": str(p.visit_id), "name": p.part_name, "part_number": p.part_number, "job_no": no} for p, no in parts]

    if "billing.read" in perms:
        raw = q.strip().upper()
        for prefix in ("INV", "FV"):
            raw = raw.removeprefix(prefix)
        raw = raw.lstrip("- #").lstrip("0")
        conds = [Invoice.customer_id.in_(select(Customer.id).where(Customer.search_text.contains(nq)))]
        if raw.isdigit():
            conds.append(Invoice.invoice_no == int(raw))
        out["invoices"] = [{"id": str(i.id), "invoice_no": i.invoice_no, "status": i.status, "total": str(i.total)}
                           for i in db.scalars(select(Invoice).where(or_(*conds)).order_by(Invoice.invoice_no.desc()).limit(limit))]
    return out
