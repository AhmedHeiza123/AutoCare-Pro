"""Shared money math for parts (no API imports, so jobs/parts/quotes can all use it)."""
from datetime import date
from decimal import Decimal
from uuid import UUID
import calendar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import to_money
from app.models import PartPurchase, PartReturn


def returned_qty(db: Session, part_id: int) -> Decimal:
    return Decimal(db.scalar(select(func.coalesce(func.sum(PartReturn.quantity), 0)).where(PartReturn.part_id == part_id)))


def returned_map(db: Session, visit_id: UUID | None = None) -> dict[int, Decimal]:
    """Returned quantity per part, optionally limited to one job."""
    query = select(PartReturn.part_id, func.sum(PartReturn.quantity)).group_by(PartReturn.part_id)
    if visit_id is not None:
        query = query.join(PartPurchase).where(PartPurchase.visit_id == visit_id)
    return {pid: Decimal(q) for pid, q in db.execute(query)}


def returned_for_parts(db: Session, part_ids: list[int]) -> dict[int, Decimal]:
    """Returned quantity for a specific set of parts in one query (use it instead of calling returned_qty per part)."""
    if not part_ids:
        return {}
    query = select(PartReturn.part_id, func.sum(PartReturn.quantity)).where(PartReturn.part_id.in_(part_ids)).group_by(PartReturn.part_id)
    return {pid: Decimal(q) for pid, q in db.execute(query)}


def effective_qty(db: Session, p: PartPurchase, returned: dict[int, Decimal] | None = None) -> Decimal:
    if p.status == "cancelled":
        return Decimal("0")
    given = returned.get(p.id, Decimal("0")) if returned is not None else returned_qty(db, p.id)
    return Decimal(p.quantity) - given


def line_cost(db: Session, p: PartPurchase, returned: dict[int, Decimal] | None = None) -> Decimal:
    return to_money(effective_qty(db, p, returned) * Decimal(p.unit_cost))


def line_price(db: Session, p: PartPurchase, returned: dict[int, Decimal] | None = None) -> Decimal:
    return to_money(effective_qty(db, p, returned) * Decimal(p.unit_price))


def parts_selling_total(db: Session, visit_id) -> Decimal:
    returned = returned_map(db, visit_id)  # one query for the whole job instead of one per part
    parts = db.scalars(select(PartPurchase).where(PartPurchase.visit_id == visit_id))
    return sum((line_price(db, p, returned) for p in parts), Decimal("0.00"))


def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def compute_totals(subtotal: Decimal, discount: Decimal, tax_rate: Decimal) -> tuple[Decimal, Decimal]:
    """Return (tax_amount, grand_total). Discount is an absolute amount; tax applies after discount."""
    net = Decimal(subtotal) - Decimal(discount)
    tax = to_money(net * Decimal(tax_rate) / 100)
    return tax, net + tax
