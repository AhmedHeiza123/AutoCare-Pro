"""Shared accounting rules, so the financial summary, the job-profit report and the invoice workflow always agree.

* Discounts are invoice-level: they are spread over Labor / Parts / Other pro rata (rounding stays in the largest category).
* COGS (cost of parts) is recognised when a part is billed on an issued invoice. Units that had already been billed and are
  later returned to the supplier reduce COGS again (in the period of the return, like a credit note reduces revenue).
  Returns of units that were never billed do not touch COGS: they were never expensed.
* A part that is on an issued invoice has its cost and price frozen (history must not change retroactively).
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import to_money
from app.models import Invoice, InvoiceItem, PartPurchase, PartReturn

ZERO = Decimal("0.00")


def allocate_discount(amounts: dict[str, Decimal], discount: Decimal) -> dict[str, Decimal]:
    """Net amount per revenue category after spreading an invoice discount pro rata; the result always sums to total - discount."""
    total = sum(amounts.values(), ZERO)
    discount = Decimal(discount)
    if not total or not discount:
        return dict(amounts)
    shares = {k: to_money(discount * v / total) for k, v in amounts.items()}
    drift = discount - sum(shares.values(), ZERO)
    if drift:
        shares[max(amounts, key=lambda k: amounts[k])] += drift
    return {k: amounts[k] - shares[k] for k in amounts}


def billed_quantity(db: Session, part_id: int) -> Decimal:
    """Quantity of this part that sits on issued invoices."""
    rows = db.scalars(select(InvoiceItem.quantity).join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                      .where(InvoiceItem.part_id == part_id, Invoice.status == "issued"))
    return sum((Decimal(q) for q in rows), ZERO)


def _billed_rows(db: Session, part_ids: list[int]) -> list[tuple]:
    return list(db.execute(select(InvoiceItem.invoice_id, Invoice.invoice_no, InvoiceItem.part_id, InvoiceItem.quantity)
                           .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
                           .where(Invoice.status == "issued", InvoiceItem.part_id.in_(part_ids))))


def billed_returned_units(db: Session, part_ids: list[int], *, start: datetime | None = None,
                          end: datetime | None = None) -> dict[int, Decimal]:
    """Per part: units that were already billed to a customer when they were returned (optionally only returns in [start, end)).

    Returns consume the units that were never billed first (quantity - billed); only the rest takes back billed units."""
    if not part_ids:
        return {}
    billed: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for _, _, pid, qty in _billed_rows(db, part_ids):
        billed[pid] += Decimal(qty)
    parts = {p.id: p for p in db.scalars(select(PartPurchase).where(PartPurchase.id.in_(part_ids)))}
    pool = {pid: max(Decimal(p.quantity) - billed[pid], ZERO) for pid, p in parts.items()}  # units never billed
    room = dict(billed)  # billed units that can still be taken back
    out: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for r in db.scalars(select(PartReturn).where(PartReturn.part_id.in_(part_ids)).order_by(PartReturn.part_id, PartReturn.returned_at, PartReturn.id)):
        qty = Decimal(r.quantity)
        use = min(qty, pool.get(r.part_id, ZERO))
        pool[r.part_id] = pool.get(r.part_id, ZERO) - use
        reduces = min(qty - use, room.get(r.part_id, ZERO))
        room[r.part_id] = room.get(r.part_id, ZERO) - reduces
        # only returns that RECOVER the cost (back to the supplier / back to the warehouse shelf) reduce COGS; a defective or used part
        # that is taken off the job is a loss: its cost stays with the job
        if reduces and r.disposition in RECOVERABLE and (start is None or start <= r.returned_at < end):
            out[r.part_id] += reduces
    return dict(out)


RECOVERABLE = ("supplier", "warehouse")


def cogs_returned_in_period(db: Session, start: datetime, end: datetime, by_source: bool = False):
    """Cost of billed units returned (to the supplier or the warehouse) during [start, end): this reduces COGS in that period.
    With by_source=True returns {'direct'|'warehouse'|'customer': amount}."""
    part_ids = list(db.scalars(select(PartReturn.part_id).distinct()))
    units = billed_returned_units(db, part_ids, start=start, end=end)
    split = {"direct": ZERO, "warehouse": ZERO, "customer": ZERO}
    if units:
        for p in db.scalars(select(PartPurchase).where(PartPurchase.id.in_(list(units)))):
            split[p.source] += to_money(units[p.id] * Decimal(p.unit_cost))
    return split if by_source else sum(split.values(), ZERO)


def invoice_part_costs(db: Session, invoice_ids: list) -> dict:
    """Net COGS per invoice (as of now): cost of the billed parts minus the billed units later returned.

    A part's returned-billed units are taken off its most recent invoices first."""
    if not invoice_ids:
        return {}
    items = list(db.execute(select(InvoiceItem.invoice_id, InvoiceItem.part_id, InvoiceItem.quantity)
                            .where(InvoiceItem.invoice_id.in_(invoice_ids), InvoiceItem.part_id.is_not(None))))
    part_ids = sorted({pid for _, pid, _ in items})
    cost = {p.id: Decimal(p.unit_cost) for p in db.scalars(select(PartPurchase).where(PartPurchase.id.in_(part_ids)))} if part_ids else {}
    result = {i: ZERO for i in invoice_ids}
    for inv_id, pid, qty in items:
        result[inv_id] += to_money(Decimal(qty) * cost[pid])
    units = billed_returned_units(db, part_ids)
    wanted = set(invoice_ids)
    for pid, remaining in units.items():
        # every issued invoice line of this part (also invoices outside the requested set), newest invoice first
        for inv_id, _, _, qty in sorted(_billed_rows(db, [pid]), key=lambda row: row[1], reverse=True):
            take = min(Decimal(qty), remaining)
            if take and inv_id in wanted:
                result[inv_id] -= to_money(take * cost[pid])
            remaining -= take
            if remaining <= 0:
                break
    return result
