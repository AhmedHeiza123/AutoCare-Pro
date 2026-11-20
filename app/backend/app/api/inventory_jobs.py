"""Repair-order side of the inventory module: the three sources of a spare part.

  A. From warehouse  -> POST /api/jobs/{id}/parts/warehouse           (stock is checked now, reserved on approval, issued when taken)
  B. Customer-supplied -> POST /api/jobs/{id}/parts/customer-supplied  (no stock, no cost, no parts revenue; labor is billed normally)
  C. Direct purchase -> the existing POST /api/jobs/{id}/parts          (unchanged; never touches the warehouse)
plus POST /api/parts/{id}/return-to-warehouse for parts that were issued but not (all) used."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.api.jobs import get_job, recompute_total, require_open
from app.api.parts import _get_part, _validate_links, part_out
from app.core.audit import audit
from app.core.errors import AppError
from app.db import get_db
from app.models import PartPurchase
from app.models.auth import User
from app.services import inventory as inv
from app.services import settings as cfg
from app.services.job_status import sync_work_status

router = APIRouter(prefix="/api", tags=["inventory-jobs"])


class WarehousePartIn(BaseModel):
    item_id: int
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)  # job-part quantities carry 2 decimals everywhere (quotes, invoices)
    warehouse_id: int | None = None
    unit_price: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)  # default: the item's selling price
    operation_id: int | None = None
    warranty_months: int | None = Field(None, ge=0, le=240)
    notes: str | None = None


@router.post("/jobs/{job_id}/parts/warehouse", status_code=201)
def add_warehouse_part(job_id: UUID, body: WarehousePartIn, request: Request, user: User = Depends(require("parts.write")),
                       db: DbSession = Depends(get_db, scope="function")):
    """Option A: take the part from the workshop warehouse. Availability is validated now; stock is NOT deducted (and not even reserved)
    just because the part was added or quoted: it is reserved when the work is approved and issued when it is actually taken."""
    if "inventory.read" not in user.permissions:
        raise AppError("ليس لديك صلاحية لهذا الإجراء", 403, "forbidden")
    job = get_job(db, job_id, lock=True)
    require_open(job)
    item = inv.get_item(db, body.item_id, active=True)
    wh = inv.get_warehouse(db, body.warehouse_id)
    _validate_links(db, job, None, body.operation_id)
    bal = inv.peek_balance(db, item.id, wh.id)
    available = bal.available if bal else Decimal("0")
    if available < body.quantity:
        raise AppError(f"الكمية المتاحة في {wh.name_ar} هي {available} فقط", 409, "insufficient_stock")
    estimate = inv.c4(bal.avg_cost) if bal and Decimal(bal.on_hand) > 0 else inv.c4(item.purchase_price)  # replaced by the real cost at issue
    default_warranty = int(cfg.get_section(db, "warranty")["default_part_months"]) or None
    p = PartPurchase(visit_id=job.id, created_by=user.id, source="warehouse", inventory_item_id=item.id, warehouse_id=wh.id,
                     part_name=(item.name_ar or item.name_en)[:200], brand=item.brand, part_number=item.sku, quantity=inv.q3(body.quantity), unit_cost=estimate,
                     unit_price=body.unit_price if body.unit_price is not None else item.selling_price, status="requested", operation_id=body.operation_id,
                     warranty_months=body.warranty_months if body.warranty_months is not None else default_warranty, notes=body.notes)
    db.add(p)
    db.flush()
    recompute_total(db, job)
    audit(db, user, "part.create_warehouse", "part", p.id, after={"item": item.sku, "qty": str(body.quantity), "warehouse": wh.code}, ip=client_ip(request))
    sync_work_status(db, job, user, "تلقائي: تمت إضافة قطعة من المخزن", client_ip(request))
    return part_out(db, p, user)


class CustomerPartIn(BaseModel):
    description: str = Field(min_length=2, max_length=160)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    operation_id: int | None = None
    warranty_months: int | None = Field(None, ge=0, le=240)  # the workshop does not warrant a part it did not supply, unless stated
    notes: str | None = None


@router.post("/jobs/{job_id}/parts/customer-supplied", status_code=201)
def add_customer_part(job_id: UUID, body: CustomerPartIn, request: Request, user: User = Depends(require("parts.write")),
                      db: DbSession = Depends(get_db, scope="function")):
    """Option B: the customer brings the part. No warehouse movement, no supplier purchase, no cost and no parts revenue; the part stays
    linked to the repair order (and to its installation labor and warranty record)."""
    job = get_job(db, job_id, lock=True)
    require_open(job)
    _validate_links(db, job, None, body.operation_id)
    p = PartPurchase(visit_id=job.id, created_by=user.id, source="customer", part_name=f"{body.description.strip()} (customer supplied / من العميل)"[:200],
                     quantity=body.quantity, unit_cost=Decimal("0"), unit_price=Decimal("0"), status="received", operation_id=body.operation_id,
                     warranty_months=body.warranty_months or None, notes=body.notes, purchased_at=datetime.now(timezone.utc))
    db.add(p)
    db.flush()
    recompute_total(db, job)
    audit(db, user, "part.create_customer", "part", p.id, after={"description": body.description, "qty": str(body.quantity)}, ip=client_ip(request))
    sync_work_status(db, job, user, "تلقائي: تمت إضافة قطعة من العميل", client_ip(request))
    return part_out(db, p, user)


class WarehouseReturnIn(BaseModel):
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    disposition: str = Field("unused", pattern="^(unused|defective|used)$")  # only 'unused' goes back to sellable stock
    reason: str = Field(min_length=2)


@router.post("/parts/{part_id}/return-to-warehouse")
def return_to_warehouse(part_id: int, body: WarehouseReturnIn, request: Request, user: User = Depends(require("parts.write")),
                        db: DbSession = Depends(get_db, scope="function")):
    p, job = _get_part(db, part_id)
    require_open(job)
    before = part_out(db, p, user)
    ret = inv.return_to_warehouse(db, p, body.quantity, body.disposition, body.reason, user)
    recompute_total(db, job)
    if p.status != before["status"]:
        sync_work_status(db, job, user, "تلقائي: تم إرجاع قطعة للمخزن", client_ip(request))
    audit(db, user, "part.return_to_warehouse", "part", p.id, before=before, after=part_out(db, p, user), reason=body.reason, ip=client_ip(request))
    return {"return_id": ret.id, "disposition": ret.disposition, "part": part_out(db, p, user)}
