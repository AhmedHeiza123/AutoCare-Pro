"""Inventory posting engine. EVERY change of stock goes through post(): one place that locks the balance row, applies the
weighted-average rules, enforces availability and writes the append-only ledger row, all inside the caller's transaction.

Concurrency: a balance row is locked (SELECT ... FOR UPDATE) before it is read, so two requests can never both take the last unit;
the database also refuses reserved > on_hand and negative stock (CHECK constraints) as a second line of defence.
Idempotency: every posting can carry a key; replaying the same key returns the original movement and changes nothing.
"""
import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (InventoryBalance, InventoryItem, PartPurchase, PartReturn, StockAdjustment, StockAdjustmentLine,
                        StockMovement, StockReservation, Warehouse)
from app.services.pricing import effective_qty

ZERO = Decimal("0")
Q3, C4 = Decimal("0.001"), Decimal("0.0001")


def q3(x) -> Decimal:
    return Decimal(str(x)).quantize(Q3, rounding=ROUND_HALF_UP)


def c4(x) -> Decimal:
    return Decimal(str(x)).quantize(C4, rounding=ROUND_HALF_UP)


# ---- lookups -------------------------------------------------------------------------------------------------------------
def default_warehouse(db: Session) -> Warehouse:
    w = db.scalar(select(Warehouse).where(Warehouse.is_default.is_(True)))
    if not w:
        raise AppError("لا يوجد مخزن افتراضي", 409, "no_default_warehouse")
    return w


def get_warehouse(db: Session, warehouse_id: int | None) -> Warehouse:
    if warehouse_id is None:
        return default_warehouse(db)
    w = db.get(Warehouse, warehouse_id)
    if not w or not w.is_active:
        raise AppError("المخزن غير موجود أو غير مفعل", 422, "bad_warehouse")
    return w


def get_item(db: Session, item_id: int, *, active: bool = False) -> InventoryItem:
    item = db.get(InventoryItem, item_id)
    if not item:
        raise AppError("صنف المخزون غير موجود", 404, "item_not_found")
    if active and not item.is_active:
        raise AppError("الصنف غير مفعل", 409, "item_inactive")
    return item


def lock_balance(db: Session, item_id: int, warehouse_id: int) -> InventoryBalance:
    """The balance row of (item, warehouse), created if missing and LOCKED for the rest of the transaction."""
    db.execute(pg_insert(InventoryBalance).values(item_id=item_id, warehouse_id=warehouse_id).on_conflict_do_nothing())
    return db.scalar(select(InventoryBalance).where(InventoryBalance.item_id == item_id, InventoryBalance.warehouse_id == warehouse_id)
                     .with_for_update().execution_options(populate_existing=True))


def peek_balance(db: Session, item_id: int, warehouse_id: int) -> InventoryBalance | None:
    return db.get(InventoryBalance, (item_id, warehouse_id))


def valuation_cost(db: Session, bal: InventoryBalance, item: InventoryItem) -> Decimal:
    """Cost at which stock that appears without a purchase (positive adjustment/count) is valued: the current average cost,
    else the last cost, else the item's reference purchase price."""
    if Decimal(bal.on_hand) > 0:
        return c4(Decimal(bal.value) / Decimal(bal.on_hand))
    return c4(bal.last_cost or item.purchase_price or ZERO)


# ---- the one posting function ---------------------------------------------------------------------------------------------
def post(db: Session, *, item_id: int, warehouse_id: int, mtype: str, qty=ZERO, reserved_delta=ZERO, cost=None, value=None,
         user=None, doc_type: str | None = None, doc_id: str | None = None, part_id: int | None = None, visit_id=None,
         reason: str | None = None, key: str | None = None, reverses_id: int | None = None) -> StockMovement:
    """Apply one movement to the balance and write its ledger row. Returns the (possibly pre-existing, for a replayed key) movement.

    qty            signed change of on-hand stock.   reserved_delta  signed change of reserved stock.
    cost           unit cost of stock coming IN.     value           exact value moved (overrides qty*cost / the average cost).
    Stock going OUT is valued at the current weighted-average cost unless `value` is given."""
    if key:
        prior = db.scalar(select(StockMovement).where(StockMovement.idempotency_key == key))
        if prior is not None:
            return prior
    qty, reserved_delta = q3(qty), q3(reserved_delta)
    bal = lock_balance(db, item_id, warehouse_id)
    on_hand, reserved, total = Decimal(bal.on_hand), Decimal(bal.reserved), Decimal(bal.value)
    unit_cost, value_delta = ZERO, ZERO
    if qty > 0:
        value_delta = c4(value) if value is not None else c4(qty * Decimal(cost if cost is not None else 0))
        unit_cost = c4(value_delta / qty)
    elif qty < 0:
        out = -qty
        if out > on_hand:
            raise AppError("الكمية المتاحة في المخزن لا تكفي", 409, "insufficient_stock")
        if value is not None:
            out_value = c4(value)
        elif out == on_hand:
            out_value = total
        else:
            out_value = c4(total * out / on_hand)
        value_delta = -out_value
        unit_cost = c4(out_value / out)
    new_on_hand, new_reserved = on_hand + qty, reserved + reserved_delta
    if new_reserved < 0:
        raise AppError("لا يمكن تحرير كمية أكبر من المحجوز", 409, "reservation_underflow")
    if new_reserved > new_on_hand:
        raise AppError("الكمية المتاحة في المخزن لا تكفي (جزء منها محجوز)", 409, "insufficient_stock")
    new_value = total + value_delta
    if new_on_hand == 0:  # no stock left: absorb any rounding dust so an empty shelf is worth exactly nothing
        value_delta, new_value = value_delta - new_value, ZERO
    if new_value < 0:
        raise AppError("قيمة المخزون لا تسمح بهذه الحركة", 409, "value_underflow")
    bal.on_hand, bal.reserved, bal.value = new_on_hand, new_reserved, new_value
    if qty > 0 and unit_cost > 0 and mtype in ("OPENING", "GOODS_RECEIPT", "RETURN_TO_WAREHOUSE", "ADJUSTMENT", "COUNT", "TRANSFER_IN"):
        bal.last_cost = unit_cost
    mv = StockMovement(item_id=item_id, warehouse_id=warehouse_id, movement_type=mtype, qty=qty, reserved_delta=reserved_delta,
                       unit_cost=unit_cost, value_delta=value_delta, on_hand_after=new_on_hand, value_after=new_value, doc_type=doc_type,
                       doc_id=doc_id, part_id=part_id, visit_id=visit_id, reason=reason, user_id=getattr(user, "id", None),
                       idempotency_key=key, reverses_id=reverses_id)
    db.add(mv)
    db.flush()
    return mv


# ---- reservations (repair-order parts) -------------------------------------------------------------------------------------
def active_reservation(db: Session, part_id: int) -> StockReservation | None:
    return db.scalar(select(StockReservation).where(StockReservation.part_id == part_id, StockReservation.status == "active")
                     .with_for_update())


def needed_qty(part: PartPurchase) -> Decimal:
    return max(q3(part.quantity) - q3(part.issued_qty), ZERO)


def sync_reservation(db: Session, part: PartPurchase, user=None, reason: str | None = None) -> StockReservation | None:
    """Make the stock held for this part equal to what is still to be issued (creates, resizes or releases the reservation)."""
    if part.source != "warehouse":
        return None
    want = needed_qty(part)
    res = active_reservation(db, part.id)
    if want <= 0:
        return release(db, part, user, reason or "nothing left to reserve") if res else None
    bal = lock_balance(db, part.inventory_item_id, part.warehouse_id)
    if res is None:
        if bal.available < want:
            raise AppError(f"الكمية المتاحة {bal.available} أقل من المطلوب {want}", 409, "insufficient_stock")
        res = StockReservation(item_id=part.inventory_item_id, warehouse_id=part.warehouse_id, part_id=part.id, qty=want, status="active", reason=reason)
        db.add(res)
        db.flush()
        post(db, item_id=res.item_id, warehouse_id=res.warehouse_id, mtype="RESERVE", reserved_delta=want, user=user,
             doc_type="job_part", doc_id=str(part.id), part_id=part.id, visit_id=part.visit_id, reason=reason)
        return res
    delta = want - Decimal(res.qty)
    if delta != 0:
        if delta > 0 and bal.available < delta:
            raise AppError(f"الكمية المتاحة {bal.available} لا تكفي لزيادة الحجز", 409, "insufficient_stock")
        res.qty = want
        post(db, item_id=res.item_id, warehouse_id=res.warehouse_id, mtype="RESERVE" if delta > 0 else "RELEASE", reserved_delta=delta, user=user,
             doc_type="job_part", doc_id=str(part.id), part_id=part.id, visit_id=part.visit_id, reason=reason or "reservation resized")
    return res


def release(db: Session, part: PartPurchase, user=None, reason: str | None = None) -> StockReservation | None:
    """Give the held stock back (rejected quotation, cancelled job or part). A no-op when nothing is reserved."""
    res = active_reservation(db, part.id)
    if res is None:
        return None
    lock_balance(db, res.item_id, res.warehouse_id)
    post(db, item_id=res.item_id, warehouse_id=res.warehouse_id, mtype="RELEASE", reserved_delta=-Decimal(res.qty), user=user,
         doc_type="job_part", doc_id=str(part.id), part_id=part.id, visit_id=part.visit_id, reason=reason or "reservation released")
    res.status, res.reason = "released", reason or res.reason
    res.closed_at = func.now()
    db.flush()
    return res


def issue_for_part(db: Session, part: PartPurchase, user=None, reason: str | None = None) -> StockMovement | None:
    """Physically issue the part to its repair order: stock leaves the shelf at the weighted-average cost, which is recorded on the
    job part (historical cost). Idempotent: a part is issued once; calling again changes nothing."""
    if part.source != "warehouse":
        return None
    need = needed_qty(part)
    if need <= 0:
        return None
    key = f"issue:{part.id}:{q3(part.issued_qty)}"
    if db.scalar(select(StockMovement.id).where(StockMovement.idempotency_key == key)):
        return None  # this exact issue was already posted (replay / race): never deduct twice
    bal = lock_balance(db, part.inventory_item_id, part.warehouse_id)
    res = active_reservation(db, part.id)
    own = Decimal(res.qty) if res else ZERO
    if Decimal(bal.on_hand) - (Decimal(bal.reserved) - own) < need:
        raise AppError(f"الكمية المتاحة في المخزن لا تكفي للصرف (المطلوب {need})", 409, "insufficient_stock")
    mv = post(db, item_id=part.inventory_item_id, warehouse_id=part.warehouse_id, mtype="ISSUE", qty=-need, reserved_delta=-own, user=user,
              doc_type="job_part", doc_id=str(part.id), part_id=part.id, visit_id=part.visit_id, reason=reason or "issued to repair order",
              key=key)
    if res is not None:
        res.status, res.closed_at = "consumed", func.now()
    part.issued_qty = q3(part.issued_qty) + need
    part.unit_cost = mv.unit_cost  # the cost of this job part is frozen at the issue-time weighted average
    if part.purchased_at is None:
        part.purchased_at = func.now()
    db.flush()
    return mv


def return_to_warehouse(db: Session, part: PartPurchase, qty, disposition: str, reason: str, user=None) -> PartReturn:
    """Take issued parts back off the repair order. 'unused' goes back to sellable stock at the cost they left with; 'defective' and
    'used' parts are NEVER put back on the shelf (their cost stays with the job)."""
    if part.source != "warehouse":
        raise AppError("هذه القطعة ليست من المخزن", 409, "not_warehouse_part")
    if disposition not in ("unused", "defective", "used"):
        raise AppError("حالة المرتجع غير صحيحة", 422, "bad_disposition")
    qty = q3(qty)
    if qty <= 0:
        raise AppError("الكمية غير صحيحة", 422, "bad_quantity")
    if q3(part.issued_qty) <= 0:
        raise AppError("لم تُصرف هذه القطعة من المخزن بعد", 409, "not_issued")
    left = effective_qty(db, part)
    if qty > left:
        raise AppError(f"الكمية المتاحة للإرجاع {left}", 422, "too_many")
    ret = PartReturn(part_id=part.id, quantity=qty, refund_amount=ZERO, reason=reason, returned_by=getattr(user, "id", None),
                     disposition="warehouse" if disposition == "unused" else disposition)
    db.add(ret)
    db.flush()
    if disposition == "unused":
        post(db, item_id=part.inventory_item_id, warehouse_id=part.warehouse_id, mtype="RETURN_TO_WAREHOUSE", qty=qty, cost=part.unit_cost,
             user=user, doc_type="job_part", doc_id=str(part.id), part_id=part.id, visit_id=part.visit_id, reason=reason,
             key=f"return:{ret.id}")
    if effective_qty(db, part) == 0:
        part.status = "returned"
    db.flush()
    return ret


def release_job_reservations(db: Session, job_id, user=None, reason: str = "repair order cancelled") -> int:
    """Release every active reservation of a job (cancelled job). Returns how many were released."""
    n = 0
    for part in db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job_id, PartPurchase.source == "warehouse")):
        if release(db, part, user, reason) is not None:
            n += 1
    return n


def issued_uninstalled_parts(db: Session, job_id) -> list[PartPurchase]:
    """Warehouse parts that left the shelf for this job but were neither installed nor returned (stock that would be lost if the job is cancelled)."""
    out = []
    for part in db.scalars(select(PartPurchase).where(PartPurchase.visit_id == job_id, PartPurchase.source == "warehouse", PartPurchase.status == "received")):
        if q3(part.issued_qty) > 0 and effective_qty(db, part) > 0:
            out.append(part)
    return out


# ---- opening balance, adjustments, counts, transfers -----------------------------------------------------------------------
def opening_balance(db: Session, item_id: int, warehouse_id: int, qty, unit_cost, user=None, key: str | None = None) -> StockMovement:
    if q3(qty) <= 0:
        raise AppError("الكمية غير صحيحة", 422, "bad_quantity")
    existing = db.scalar(select(StockMovement.id).where(StockMovement.item_id == item_id, StockMovement.warehouse_id == warehouse_id,
                                                        StockMovement.movement_type == "OPENING"))
    if existing and not (key and db.scalar(select(StockMovement.id).where(StockMovement.idempotency_key == key))):
        raise AppError("الرصيد الافتتاحي مسجل لهذا الصنف في هذا المخزن", 409, "opening_exists")
    return post(db, item_id=item_id, warehouse_id=warehouse_id, mtype="OPENING", qty=qty, cost=unit_cost, user=user,
                doc_type="opening", doc_id=f"{item_id}:{warehouse_id}", reason="opening balance", key=key)


def _adjustment(db: Session, kind: str, warehouse_id: int, lines: list[dict], reason: str, user, key: str | None) -> StockAdjustment:
    if key:
        prior = db.scalar(select(StockAdjustment).where(StockAdjustment.idempotency_key == key))
        if prior is not None:
            return prior
    if not lines:
        raise AppError("أضف صنفًا واحدًا على الأقل", 422, "no_lines")
    if len({ln["item_id"] for ln in lines}) != len(lines):
        raise AppError("الصنف مكرر في نفس المستند", 422, "duplicate_item")
    adj = StockAdjustment(kind=kind, warehouse_id=warehouse_id, reason=reason, created_by=getattr(user, "id", None), idempotency_key=key)
    db.add(adj)
    db.flush()
    for ln in sorted(lines, key=lambda x: x["item_id"]):  # fixed lock order avoids deadlocks between concurrent documents
        item = get_item(db, ln["item_id"])
        bal = lock_balance(db, item.id, warehouse_id)
        system = Decimal(bal.on_hand)
        if kind == "count":
            counted = q3(ln["counted_qty"])
            if counted < 0:
                raise AppError("الكمية المعدودة غير صحيحة", 422, "bad_quantity")
            delta = counted - system
        else:
            counted, delta = None, q3(ln["qty_delta"])
        cost = valuation_cost(db, bal, item)
        mv = None
        if delta != 0:
            mv = post(db, item_id=item.id, warehouse_id=warehouse_id, mtype="COUNT" if kind == "count" else "ADJUSTMENT", qty=delta,
                      cost=cost if delta > 0 else None, user=user, doc_type=kind, doc_id=str(adj.id), reason=reason,
                      key=f"{key}:{item.id}" if key else None)
        db.add(StockAdjustmentLine(adjustment_id=adj.id, item_id=item.id, system_qty=system, counted_qty=counted, qty_delta=delta,
                                   unit_cost=mv.unit_cost if mv else cost, movement_id=mv.id if mv else None))
    db.flush()
    return adj


def adjust(db: Session, warehouse_id: int, lines: list[dict], reason: str, user=None, key: str | None = None) -> StockAdjustment:
    return _adjustment(db, "adjustment", warehouse_id, lines, reason, user, key)


def physical_count(db: Session, warehouse_id: int, lines: list[dict], reason: str, user=None, key: str | None = None) -> StockAdjustment:
    return _adjustment(db, "count", warehouse_id, lines, reason, user, key)


def transfer(db: Session, from_wh: int, to_wh: int, lines: list[dict], reason: str, user=None, key: str | None = None) -> str:
    """Move stock between warehouses at the cost it leaves with. Returns the document id shared by the paired movements."""
    if from_wh == to_wh:
        raise AppError("المخزن المصدر والوجهة متطابقان", 422, "same_warehouse")
    if not lines:
        raise AppError("أضف صنفًا واحدًا على الأقل", 422, "no_lines")
    get_warehouse(db, from_wh)
    get_warehouse(db, to_wh)
    doc = str(uuid.uuid5(uuid.NAMESPACE_URL, key)) if key else str(uuid.uuid4())  # a replayed key re-uses every posted movement
    for ln in sorted(lines, key=lambda x: x["item_id"]):
        item = get_item(db, ln["item_id"])
        out = post(db, item_id=item.id, warehouse_id=from_wh, mtype="TRANSFER_OUT", qty=-q3(ln["qty"]), user=user, doc_type="transfer", doc_id=doc,
                   reason=reason, key=f"{key}:out:{item.id}" if key else None)
        post(db, item_id=item.id, warehouse_id=to_wh, mtype="TRANSFER_IN", qty=q3(ln["qty"]), value=-Decimal(out.value_delta), user=user,
             doc_type="transfer", doc_id=doc, reason=reason, key=f"{key}:in:{item.id}" if key else None)
    return doc


def reverse_movement(db: Session, movement_id: int, reason: str, user=None) -> StockMovement:
    """Undo an opening balance / adjustment / count with an equal and opposite REVERSAL row (the original is never edited)."""
    mv = db.get(StockMovement, movement_id)
    if not mv:
        raise AppError("الحركة غير موجودة", 404, "not_found")
    if mv.movement_type not in ("OPENING", "ADJUSTMENT", "COUNT"):
        raise AppError("هذا النوع من الحركات لا يُعكس مباشرة؛ استخدم مستند العكس الخاص به", 409, "not_reversible")
    if db.scalar(select(StockMovement.id).where(StockMovement.reverses_id == mv.id)):
        raise AppError("الحركة معكوسة بالفعل", 409, "already_reversed")
    qty = Decimal(mv.qty)
    if qty == 0:
        raise AppError("هذه الحركة لا تغيّر الرصيد", 409, "not_reversible")
    # an inflow is undone by taking exactly its value out again, an outflow by putting exactly its value back
    return post(db, item_id=mv.item_id, warehouse_id=mv.warehouse_id, mtype="REVERSAL", qty=-qty, value=abs(Decimal(mv.value_delta)), user=user,
                doc_type=mv.doc_type, doc_id=mv.doc_id, reason=reason, reverses_id=mv.id)
