"""Supplier purchase invoices, goods receipts, supplier payments and credits.

Three separate events (never mixed up):
  1. the supplier invoice is POSTED  -> we owe the supplier (liability); stock does not change;
  2. goods are RECEIVED (full or partial) -> stock and inventory value increase, at the invoice's net cost;
  3. the supplier is PAID -> the liability falls; stock does not change.
None of them is an operating expense: the cost reaches the profit report only when stock is consumed (job COGS)."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.money import to_money
from app.models import (GoodsReceipt, GoodsReceiptLine, InventoryItem, PurchaseInvoice, PurchaseInvoiceLine, StockMovement, Supplier,
                        SupplierCredit, SupplierPayment)
from app.services import inventory as inv

ZERO = Decimal("0.00")


# ---- arithmetic -------------------------------------------------------------------------------------------------------------
def line_total(qty, unit_cost, discount) -> Decimal:
    total = to_money(inv.q3(qty) * Decimal(str(unit_cost))) - to_money(discount)
    if total < 0:
        raise AppError("خصم السطر أكبر من قيمته", 422, "bad_discount")
    return total


def recalc(db: Session, invoice: PurchaseInvoice) -> None:
    db.flush()
    subtotal = sum((Decimal(r) for r in db.scalars(select(PurchaseInvoiceLine.line_total).where(PurchaseInvoiceLine.invoice_id == invoice.id))), ZERO)
    if Decimal(invoice.discount) > subtotal:
        raise AppError("خصم الفاتورة أكبر من إجماليها", 422, "bad_discount")
    net = subtotal - Decimal(invoice.discount)
    invoice.subtotal = subtotal
    invoice.tax_amount = to_money(net * Decimal(invoice.tax_rate) / 100)
    invoice.total = net + Decimal(invoice.tax_amount)


def net_line_value(invoice: PurchaseInvoice, line: PurchaseInvoiceLine) -> Decimal:
    """What this line costs us net of the line discount AND its share of the invoice discount (tax is recoverable, not stock cost)."""
    total = Decimal(line.line_total)
    if Decimal(invoice.subtotal) > 0 and Decimal(invoice.discount) > 0:
        total -= Decimal(invoice.discount) * total / Decimal(invoice.subtotal)
    return inv.c4(total)


# ---- invoices ---------------------------------------------------------------------------------------------------------------
def _lock(db: Session, invoice_id) -> PurchaseInvoice:
    invoice = db.scalar(select(PurchaseInvoice).where(PurchaseInvoice.id == invoice_id).with_for_update().execution_options(populate_existing=True))
    if not invoice:
        raise AppError("فاتورة المشتريات غير موجودة", 404, "not_found")
    return invoice


def _check_supplier_number(db: Session, supplier_id: int, number: str, exclude=None) -> None:
    q = select(PurchaseInvoice.id).where(PurchaseInvoice.supplier_id == supplier_id, func.lower(PurchaseInvoice.supplier_invoice_no) == number.strip().lower(),
                                         PurchaseInvoice.status != "cancelled")
    if exclude:
        q = q.where(PurchaseInvoice.id != exclude)
    if db.scalar(q):
        raise AppError("رقم فاتورة المورد مسجل من قبل لنفس المورد", 409, "duplicate_supplier_invoice")


def _set_lines(db: Session, invoice: PurchaseInvoice, lines: list[dict]) -> None:
    if not lines:
        raise AppError("أضف صنفًا واحدًا على الأقل", 422, "no_lines")
    for existing in db.scalars(select(PurchaseInvoiceLine).where(PurchaseInvoiceLine.invoice_id == invoice.id)):
        db.delete(existing)
    db.flush()
    for ln in lines:
        item = inv.get_item(db, ln["item_id"], active=True)
        qty = inv.q3(ln["qty"])
        if qty <= 0:
            raise AppError("الكمية غير صحيحة", 422, "bad_quantity")
        db.add(PurchaseInvoiceLine(invoice_id=invoice.id, item_id=item.id, qty_ordered=qty, unit_cost=inv.c4(ln["unit_cost"]),
                                   discount=to_money(ln.get("discount", 0)), line_total=line_total(qty, ln["unit_cost"], ln.get("discount", 0))))
    db.flush()


def create_draft(db: Session, *, supplier_id: int, supplier_invoice_no: str, invoice_date: date, warehouse_id: int | None, lines: list[dict],
                 discount=0, tax_rate=0, notes: str | None = None, user=None, key: str | None = None) -> PurchaseInvoice:
    if key:
        prior = db.scalar(select(PurchaseInvoice).where(PurchaseInvoice.idempotency_key == key))
        if prior is not None:
            return prior
    supplier = db.get(Supplier, supplier_id)
    if not supplier or not supplier.is_active:
        raise AppError("المورد غير موجود أو غير مفعل", 422, "bad_supplier")
    _check_supplier_number(db, supplier_id, supplier_invoice_no)
    wh = inv.get_warehouse(db, warehouse_id)
    invoice = PurchaseInvoice(supplier_id=supplier_id, supplier_invoice_no=supplier_invoice_no.strip(), invoice_date=invoice_date, warehouse_id=wh.id,
                              discount=to_money(discount), tax_rate=Decimal(str(tax_rate)), notes=notes, created_by=getattr(user, "id", None),
                              idempotency_key=key, status="draft")
    db.add(invoice)
    db.flush()
    _set_lines(db, invoice, lines)
    recalc(db, invoice)
    return invoice


def update_draft(db: Session, invoice_id, *, supplier_invoice_no=None, invoice_date=None, warehouse_id=None, lines=None, discount=None, tax_rate=None,
                 notes=None) -> PurchaseInvoice:
    invoice = _lock(db, invoice_id)
    if invoice.status != "draft":
        raise AppError("الفاتورة مرحّلة ولا يمكن تعديلها", 409, "invoice_posted")
    if supplier_invoice_no is not None:
        _check_supplier_number(db, invoice.supplier_id, supplier_invoice_no, exclude=invoice.id)
        invoice.supplier_invoice_no = supplier_invoice_no.strip()
    if invoice_date is not None:
        invoice.invoice_date = invoice_date
    if warehouse_id is not None:
        invoice.warehouse_id = inv.get_warehouse(db, warehouse_id).id
    if discount is not None:
        invoice.discount = to_money(discount)
    if tax_rate is not None:
        invoice.tax_rate = Decimal(str(tax_rate))
    if notes is not None:
        invoice.notes = notes
    if lines is not None:
        _set_lines(db, invoice, lines)
    recalc(db, invoice)
    return invoice


def delete_draft(db: Session, invoice_id) -> None:
    invoice = _lock(db, invoice_id)
    if invoice.status != "draft":
        raise AppError("لا يمكن حذف إلا الفاتورة المسودة", 409, "invoice_posted")
    for line in db.scalars(select(PurchaseInvoiceLine).where(PurchaseInvoiceLine.invoice_id == invoice.id)):
        db.delete(line)
    db.flush()
    db.delete(invoice)


def post_invoice(db: Session, invoice_id) -> PurchaseInvoice:
    invoice = _lock(db, invoice_id)
    if invoice.status == "posted":
        return invoice  # idempotent
    if invoice.status != "draft":
        raise AppError("الفاتورة ملغاة", 409, "invoice_cancelled")
    if not db.scalar(select(PurchaseInvoiceLine.id).where(PurchaseInvoiceLine.invoice_id == invoice.id).limit(1)):
        raise AppError("أضف صنفًا واحدًا على الأقل", 422, "no_lines")
    invoice.status, invoice.posted_at = "posted", func.now()
    db.flush()
    return invoice


def money(db: Session, invoice: PurchaseInvoice) -> dict:
    paid = to_money(db.scalar(select(func.coalesce(func.sum(SupplierPayment.amount), 0)).where(SupplierPayment.invoice_id == invoice.id)))
    credits = to_money(db.scalar(select(func.coalesce(func.sum(SupplierCredit.amount), 0)).where(SupplierCredit.invoice_id == invoice.id)))
    due = Decimal(invoice.total) - credits
    outstanding = due - paid
    if invoice.status != "posted":
        status = invoice.status
    elif outstanding <= 0:
        status = "paid"
    elif paid > 0:
        status = "partial"
    else:
        status = "unpaid"
    return {"paid": paid, "credits": credits, "outstanding": outstanding, "payment_status": status}


def cancel_invoice(db: Session, invoice_id, reason: str) -> PurchaseInvoice:
    invoice = _lock(db, invoice_id)
    if invoice.status == "cancelled":
        return invoice
    if invoice.status == "posted":
        if db.scalar(select(GoodsReceipt.id).where(GoodsReceipt.invoice_id == invoice.id, GoodsReceipt.status == "posted").limit(1)):
            raise AppError("تم استلام بضاعة على هذه الفاتورة؛ اعكس الاستلام أولًا", 409, "has_receipts")
        m = money(db, invoice)
        if m["paid"] > 0 or m["credits"] > 0:
            raise AppError("على الفاتورة مدفوعات أو إشعارات دائنة للمورد ولا يمكن إلغاؤها", 409, "has_payments")
    invoice.status, invoice.cancelled_at, invoice.cancel_reason = "cancelled", func.now(), reason
    db.flush()
    return invoice


# ---- goods receipt -----------------------------------------------------------------------------------------------------------
def _receipt_status(db: Session, invoice: PurchaseInvoice) -> None:
    rows = list(db.execute(select(PurchaseInvoiceLine.qty_ordered, PurchaseInvoiceLine.qty_received).where(PurchaseInvoiceLine.invoice_id == invoice.id)))
    received = sum((Decimal(r) for _, r in rows), Decimal("0"))
    if received == 0:
        invoice.receipt_status = "none"
    elif all(Decimal(o) == Decimal(r) for o, r in rows):
        invoice.receipt_status = "full"
    else:
        invoice.receipt_status = "partial"


def receive_goods(db: Session, invoice_id, lines: list[dict], user=None, key: str | None = None, notes: str | None = None) -> GoodsReceipt:
    """Register goods that physically arrived (partial allowed). Stock and value increase ONLY here."""
    if key:
        prior = db.scalar(select(GoodsReceipt).where(GoodsReceipt.idempotency_key == key))
        if prior is not None:
            return prior
    invoice = _lock(db, invoice_id)
    if key:  # re-check now that we hold the invoice lock: a concurrent identical request may have just committed
        prior = db.scalar(select(GoodsReceipt).where(GoodsReceipt.idempotency_key == key))
        if prior is not None:
            return prior
    if invoice.status != "posted":
        raise AppError("لا يمكن الاستلام إلا على فاتورة مرحّلة", 409, "not_posted")
    if not lines:
        raise AppError("حدد الأصناف المستلمة", 422, "no_lines")
    ids = [ln["invoice_line_id"] for ln in lines]
    if len(set(ids)) != len(ids):
        raise AppError("السطر مكرر في نفس الاستلام", 422, "duplicate_line")
    by_id = {l.id: l for l in db.scalars(select(PurchaseInvoiceLine).where(PurchaseInvoiceLine.invoice_id == invoice.id, PurchaseInvoiceLine.id.in_(ids))
                                         .order_by(PurchaseInvoiceLine.item_id, PurchaseInvoiceLine.id).with_for_update())}
    if len(by_id) != len(ids):
        raise AppError("سطر لا يخص هذه الفاتورة", 422, "bad_line")
    receipt = GoodsReceipt(invoice_id=invoice.id, warehouse_id=invoice.warehouse_id, received_by=getattr(user, "id", None), notes=notes,
                           idempotency_key=key, status="posted")
    db.add(receipt)
    db.flush()
    wanted = {ln["invoice_line_id"]: inv.q3(ln["qty"]) for ln in lines}
    for line in sorted(by_id.values(), key=lambda l: (l.item_id, l.id)):  # fixed lock order
        qty = wanted[line.id]
        remaining = Decimal(line.qty_ordered) - Decimal(line.qty_received)
        if qty <= 0:
            raise AppError("الكمية غير صحيحة", 422, "bad_quantity")
        if qty > remaining:
            raise AppError(f"الكمية المستلمة أكبر من المتبقي على السطر ({remaining})", 409, "over_receipt")
        net = net_line_value(invoice, line)
        value = (net - Decimal(line.received_value)) if qty == remaining else inv.c4(net * qty / Decimal(line.qty_ordered))
        mv = inv.post(db, item_id=line.item_id, warehouse_id=invoice.warehouse_id, mtype="GOODS_RECEIPT", qty=qty, value=value, user=user,
                      doc_type="goods_receipt", doc_id=str(receipt.id), reason=f"supplier invoice {invoice.supplier_invoice_no}",
                      key=f"{key}:{line.id}" if key else None)
        line.qty_received = Decimal(line.qty_received) + qty
        line.received_value = Decimal(line.received_value) + value
        db.add(GoodsReceiptLine(receipt_id=receipt.id, invoice_line_id=line.id, item_id=line.item_id, qty=qty, unit_cost=mv.unit_cost, value=value,
                                movement_id=mv.id))
    db.flush()
    _receipt_status(db, invoice)
    return receipt


def reverse_receipt(db: Session, receipt_id, reason: str, user=None) -> GoodsReceipt:
    receipt = db.scalar(select(GoodsReceipt).where(GoodsReceipt.id == receipt_id).with_for_update().execution_options(populate_existing=True))
    if not receipt:
        raise AppError("إذن الاستلام غير موجود", 404, "not_found")
    if receipt.status == "reversed":
        return receipt
    invoice = _lock(db, receipt.invoice_id)
    rows = list(db.scalars(select(GoodsReceiptLine).where(GoodsReceiptLine.receipt_id == receipt.id).order_by(GoodsReceiptLine.item_id, GoodsReceiptLine.id)))
    for row in rows:
        line = db.get(PurchaseInvoiceLine, row.invoice_line_id, with_for_update=True, populate_existing=True)
        try:
            inv.post(db, item_id=row.item_id, warehouse_id=receipt.warehouse_id, mtype="REVERSAL", qty=-Decimal(row.qty), value=Decimal(row.value), user=user,
                     doc_type="goods_receipt", doc_id=str(receipt.id), reason=reason, reverses_id=row.movement_id)
        except AppError as e:
            if e.code in ("insufficient_stock", "value_underflow"):
                raise AppError("لا يمكن عكس الاستلام لأن جزءًا من الكمية صُرف أو حُجز", 409, "stock_already_used") from e
            raise
        line.qty_received = Decimal(line.qty_received) - Decimal(row.qty)
        line.received_value = Decimal(line.received_value) - Decimal(row.value)
    receipt.status, receipt.reversed_at, receipt.reverse_reason = "reversed", func.now(), reason
    db.flush()
    _receipt_status(db, invoice)
    return receipt


# ---- supplier money ----------------------------------------------------------------------------------------------------------
def pay_invoice(db: Session, invoice_id, *, amount, method: str, reference=None, note=None, user=None, key: str | None = None) -> SupplierPayment:
    """Pay a supplier. Independent of goods receipts: you can pay before or after the goods arrive."""
    if key:
        prior = db.scalar(select(SupplierPayment).where(SupplierPayment.idempotency_key == key))
        if prior is not None:
            return prior
    invoice = _lock(db, invoice_id)
    if key:
        prior = db.scalar(select(SupplierPayment).where(SupplierPayment.idempotency_key == key))
        if prior is not None:
            return prior
    if invoice.status != "posted":
        raise AppError("لا يمكن تسجيل دفعة إلا على فاتورة مرحّلة", 409, "not_posted")
    amount = to_money(amount)
    if amount <= 0:
        raise AppError("المبلغ غير صحيح", 422, "bad_amount")
    outstanding = money(db, invoice)["outstanding"]
    if amount > outstanding:
        raise AppError(f"المبلغ أكبر من المتبقي للمورد ({outstanding})", 422, "overpayment")
    pay = SupplierPayment(invoice_id=invoice.id, supplier_id=invoice.supplier_id, amount=amount, method=method, reference=reference, note=note,
                          paid_by=getattr(user, "id", None), idempotency_key=key)
    db.add(pay)
    db.flush()
    return pay


def add_supplier_credit(db: Session, *, supplier_id: int, amount, reason: str, invoice_id=None, movement_id=None, user=None) -> SupplierCredit:
    amount = to_money(amount)
    if amount <= 0:
        raise AppError("المبلغ غير صحيح", 422, "bad_amount")
    if invoice_id is not None:
        invoice = _lock(db, invoice_id)
        if invoice.supplier_id != supplier_id or invoice.status != "posted":
            raise AppError("الفاتورة لا تخص هذا المورد أو غير مرحّلة", 422, "bad_invoice")
        if amount > money(db, invoice)["outstanding"]:
            raise AppError("مبلغ الإشعار أكبر من المتبقي على الفاتورة", 422, "credit_too_large")
    credit = SupplierCredit(supplier_id=supplier_id, invoice_id=invoice_id, amount=amount, reason=reason, movement_id=movement_id, created_by=getattr(user, "id", None))
    db.add(credit)
    db.flush()
    return credit


def supplier_return(db: Session, *, item_id: int, warehouse_id: int, qty, supplier_id: int, credit_amount=0, invoice_id=None, reason: str, user=None,
                    key: str | None = None) -> StockMovement:
    """Send stock back to the supplier: stock leaves at the average cost; any credit the supplier gives reduces what we owe."""
    qty = inv.q3(qty)
    if qty <= 0:
        raise AppError("الكمية غير صحيحة", 422, "bad_quantity")
    if not db.get(Supplier, supplier_id):
        raise AppError("المورد غير موجود", 422, "bad_supplier")
    prior = db.scalar(select(StockMovement).where(StockMovement.idempotency_key == key)) if key else None
    if prior is not None:
        return prior
    mv = inv.post(db, item_id=item_id, warehouse_id=warehouse_id, mtype="SUPPLIER_RETURN", qty=-qty, user=user, doc_type="supplier_return",
                  doc_id=str(uuid.uuid4()), reason=reason, key=key)
    if to_money(credit_amount) > 0:
        add_supplier_credit(db, supplier_id=supplier_id, amount=credit_amount, reason=reason, invoice_id=invoice_id, movement_id=mv.id, user=user)
    return mv


def supplier_balances(db: Session) -> list[dict]:
    """What we owe each supplier: posted invoices − payments − credits (goods not yet received still count: the invoice is a liability)."""
    out = []
    for s in db.scalars(select(Supplier).order_by(Supplier.name)):
        billed = to_money(db.scalar(select(func.coalesce(func.sum(PurchaseInvoice.total), 0)).where(PurchaseInvoice.supplier_id == s.id, PurchaseInvoice.status == "posted")))
        paid = to_money(db.scalar(select(func.coalesce(func.sum(SupplierPayment.amount), 0)).where(SupplierPayment.supplier_id == s.id)))
        credits = to_money(db.scalar(select(func.coalesce(func.sum(SupplierCredit.amount), 0)).where(SupplierCredit.supplier_id == s.id)))
        if billed or paid or credits:
            out.append({"supplier_id": s.id, "supplier": s.name, "invoiced": billed, "paid": paid, "credits": credits, "outstanding": billed - paid - credits})
    return out
