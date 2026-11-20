"""Inventory, purchasing and parts-profit reports, in the same shape as app.api.reports (each returns (columns, rows)).

Cash-flow reports (supplier payments) and accrual reports (purchases posted, COGS) are labelled as such. Cost / value columns are only
shown to users with inventory.costs."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.core.money import to_money
from app.models import (Customer, InventoryBalance, InventoryCategory, InventoryItem, Invoice, InvoiceItem, PartPurchase, PurchaseInvoice, StockAdjustment,
                        StockAdjustmentLine, StockMovement, Supplier, SupplierPayment, User, Vehicle, VehicleVisit, Warehouse)
from app.services import purchasing as pur
from app.services.accounting import cogs_returned_in_period
from app.services.inventory import c4

ZERO = Decimal("0")


def _costs(c) -> bool:
    return "inventory.costs" in c.user.permissions


def n(x) -> str:
    """Quantities keep up to 3 decimals but no trailing zeros (2.500 -> 2.5)."""
    d = Decimal(x or 0)
    return f"{d:f}".rstrip("0").rstrip(".") if "." in f"{d:f}" else f"{d:f}"


def m(x) -> str:
    return f"{Decimal(x or 0):.2f}"


def _local(dt) -> str | None:
    from app.api.reports import local
    return local(dt)


# ---- inventory ---------------------------------------------------------------------------------------------------------------
def r_stock(c):
    cols = [("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("warehouse", "المخزن", "text"), ("on_hand", "الرصيد", "text"), ("reserved", "المحجوز", "text"),
            ("available", "المتاح", "text"), ("min_stock", "الحد الأدنى", "text")]
    if _costs(c):
        cols += [("avg_cost", "متوسط التكلفة", "money"), ("value", "قيمة المخزون", "money")]
    rows = []
    q = select(InventoryBalance, InventoryItem, Warehouse).join(InventoryItem, InventoryItem.id == InventoryBalance.item_id) \
        .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id).where(InventoryBalance.on_hand > 0).order_by(InventoryItem.name_en, Warehouse.id)
    for b, i, w in c.db.execute(q):
        r = {"sku": i.sku, "name": i.name_ar or i.name_en, "warehouse": w.name_ar, "on_hand": n(b.on_hand), "reserved": n(b.reserved), "available": n(b.available),
             "min_stock": n(i.min_stock)}
        if _costs(c):
            r.update(avg_cost=m(c4(b.avg_cost)), value=m(b.value))
        rows.append(r)
    return cols, rows


def r_valuation(c):
    cols = [("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("warehouse", "المخزن", "text"), ("on_hand", "الكمية", "text"),
            ("avg_cost", "متوسط التكلفة", "money"), ("value", "قيمة المخزون", "money")]
    rows = []
    q = select(InventoryBalance, InventoryItem, Warehouse).join(InventoryItem, InventoryItem.id == InventoryBalance.item_id) \
        .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id).where(InventoryBalance.on_hand > 0).order_by(InventoryItem.name_en)
    for b, i, w in c.db.execute(q):
        rows.append({"sku": i.sku, "name": i.name_ar or i.name_en, "warehouse": w.name_ar, "on_hand": n(b.on_hand), "avg_cost": m(c4(b.avg_cost)), "value": m(b.value)})
    return cols, rows


def _item_totals(c):
    bal = select(InventoryBalance.item_id, func.sum(InventoryBalance.on_hand).label("o"), func.sum(InventoryBalance.reserved).label("r")).group_by(InventoryBalance.item_id).subquery()
    return c.db.execute(select(InventoryItem, func.coalesce(bal.c.o, 0), func.coalesce(bal.c.r, 0)).outerjoin(bal, bal.c.item_id == InventoryItem.id)
                        .where(InventoryItem.is_active.is_(True)).order_by(InventoryItem.name_en)).all()


def r_low_stock(c):
    cols = [("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("on_hand", "الرصيد", "text"), ("available", "المتاح", "text"), ("min_stock", "الحد الأدنى", "text"),
            ("reorder", "كمية إعادة الطلب", "text"), ("suggested", "المقترح طلبه", "text")]
    rows = []
    for i, o, r in _item_totals(c):
        avail = Decimal(o) - Decimal(r)
        if Decimal(i.min_stock) > 0 and avail <= Decimal(i.min_stock):
            rows.append({"sku": i.sku, "name": i.name_ar or i.name_en, "on_hand": n(o), "available": n(avail), "min_stock": n(i.min_stock), "reorder": n(i.reorder_qty),
                         "suggested": n(max(Decimal(i.reorder_qty), Decimal(i.min_stock) - avail))})
    return cols, rows


def r_out_of_stock(c):
    cols = [("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("min_stock", "الحد الأدنى", "text"), ("location", "مكان التخزين", "text")]
    return cols, [{"sku": i.sku, "name": i.name_ar or i.name_en, "min_stock": n(i.min_stock), "location": i.storage_location}
                  for i, o, _ in _item_totals(c) if Decimal(o) <= 0]


def r_movements(c):
    cols = [("date", "التاريخ", "text"), ("type", "النوع", "text"), ("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("qty", "الكمية", "text"),
            ("reserved", "تغيّر المحجوز", "text"), ("after", "الرصيد بعد", "text"), ("doc", "المستند", "text"), ("user", "المستخدم", "text"), ("reason", "السبب", "text")]
    if _costs(c):
        cols += [("unit_cost", "تكلفة الوحدة", "money"), ("value", "القيمة", "money")]
    rows = []
    q = select(StockMovement, InventoryItem, User.username).join(InventoryItem, InventoryItem.id == StockMovement.item_id) \
        .outerjoin(User, User.id == StockMovement.user_id).where(StockMovement.ts >= c.start, StockMovement.ts < c.end).order_by(StockMovement.id)
    for mv, i, uname in c.db.execute(q):
        r = {"date": _local(mv.ts), "type": mv.movement_type, "sku": i.sku, "name": i.name_ar or i.name_en, "qty": n(mv.qty), "reserved": n(mv.reserved_delta),
             "after": n(mv.on_hand_after), "doc": f"{mv.doc_type or ''} {mv.doc_id or ''}".strip(), "user": uname, "reason": mv.reason}
        if _costs(c):
            r.update(unit_cost=m(mv.unit_cost), value=m(mv.value_delta))
        rows.append(r)
    return cols, rows


def r_adjustments(c):
    cols = [("date", "التاريخ", "text"), ("number", "رقم المستند", "text"), ("kind", "النوع", "text"), ("sku", "كود الصنف", "text"), ("name", "الصنف", "text"),
            ("system", "رصيد النظام", "text"), ("counted", "المعدود", "text"), ("delta", "الفرق", "text"), ("reason", "السبب", "text")]
    if _costs(c):
        cols.append(("value", "قيمة الفرق", "money"))
    rows = []
    q = select(StockAdjustment, StockAdjustmentLine, InventoryItem).join(StockAdjustmentLine, StockAdjustmentLine.adjustment_id == StockAdjustment.id) \
        .join(InventoryItem, InventoryItem.id == StockAdjustmentLine.item_id).where(StockAdjustment.created_at >= c.start, StockAdjustment.created_at < c.end) \
        .order_by(StockAdjustment.number, StockAdjustmentLine.id)
    for a, l, i in c.db.execute(q):
        r = {"date": _local(a.created_at), "number": str(a.number), "kind": a.kind, "sku": i.sku, "name": i.name_ar or i.name_en, "system": n(l.system_qty),
             "counted": n(l.counted_qty) if l.counted_qty is not None else "", "delta": n(l.qty_delta), "reason": a.reason}
        if _costs(c):
            r["value"] = m(Decimal(l.qty_delta) * Decimal(l.unit_cost))
        rows.append(r)
    return cols, rows


def _issued_by_item(c, start, end) -> dict:
    issued = {i: Decimal(q) for i, q in c.db.execute(select(StockMovement.item_id, func.coalesce(func.sum(-StockMovement.qty), 0))
                                                     .where(StockMovement.movement_type == "ISSUE", StockMovement.ts >= start, StockMovement.ts < end).group_by(StockMovement.item_id))}
    for i, q in c.db.execute(select(StockMovement.item_id, func.coalesce(func.sum(StockMovement.qty), 0))
                             .where(StockMovement.movement_type == "RETURN_TO_WAREHOUSE", StockMovement.ts >= start, StockMovement.ts < end).group_by(StockMovement.item_id)):
        issued[i] = issued.get(i, ZERO) - Decimal(q)
    return issued


def r_fast_moving(c):
    cols = [("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("issued", "المصروف في الفترة", "text"), ("on_hand", "الرصيد الحالي", "text")]
    issued = _issued_by_item(c, c.start, c.end)
    totals = {i.id: (i, o) for i, o, _ in _item_totals(c)}
    rows = [{"sku": totals[i][0].sku, "name": totals[i][0].name_ar or totals[i][0].name_en, "issued": n(q), "on_hand": n(totals[i][1])}
            for i, q in sorted(issued.items(), key=lambda kv: kv[1], reverse=True) if q > 0 and i in totals]
    return cols, rows[:50]


def r_slow_moving(c):
    days = int(c.p.get("days", 90))
    cols = [("sku", "كود الصنف", "text"), ("name", "الصنف", "text"), ("on_hand", "الرصيد الحالي", "text"), ("issued", f"المصروف آخر {days} يوم", "text"),
            ("last_issue", "آخر صرف", "text")]
    now = datetime.now(timezone.utc)
    issued = _issued_by_item(c, now - timedelta(days=days), now + timedelta(days=1))
    last = {i: t for i, t in c.db.execute(select(StockMovement.item_id, func.max(StockMovement.ts)).where(StockMovement.movement_type == "ISSUE").group_by(StockMovement.item_id))}
    rows = [{"sku": i.sku, "name": i.name_ar or i.name_en, "on_hand": n(o), "issued": n(issued.get(i.id, ZERO)), "last_issue": _local(last.get(i.id)) or ""}
            for i, o, _ in _item_totals(c) if Decimal(o) > 0 and issued.get(i.id, ZERO) <= 0]
    return cols, rows


# ---- purchasing ----------------------------------------------------------------------------------------------------------------
def r_purchases_by_supplier(c):
    cols = [("supplier", "المورد", "text"), ("invoices", "عدد الفواتير", "int"), ("net", "المشتريات (بدون ضريبة)", "money"), ("tax", "الضريبة", "money"), ("total", "الإجمالي", "money")]
    rows = []
    q = select(Supplier.name, func.count(PurchaseInvoice.id), func.coalesce(func.sum(PurchaseInvoice.subtotal - PurchaseInvoice.discount), 0),
               func.coalesce(func.sum(PurchaseInvoice.tax_amount), 0), func.coalesce(func.sum(PurchaseInvoice.total), 0)) \
        .join(PurchaseInvoice, PurchaseInvoice.supplier_id == Supplier.id).where(PurchaseInvoice.status == "posted", PurchaseInvoice.invoice_date >= c.a, PurchaseInvoice.invoice_date <= c.b) \
        .group_by(Supplier.name).order_by(Supplier.name)
    for name, cnt, net, tax, total in c.db.execute(q):
        rows.append({"supplier": name, "invoices": cnt, "net": m(net), "tax": m(tax), "total": m(total)})
    return cols, rows


def r_supplier_invoices(c):
    cols = [("number", "رقم الفاتورة الداخلي", "text"), ("supplier", "المورد", "text"), ("supplier_no", "رقم فاتورة المورد", "text"), ("date", "التاريخ", "text"), ("status", "الحالة", "text"),
            ("receipt", "الاستلام", "text"), ("payment", "السداد", "text"), ("total", "الإجمالي", "money"), ("paid", "المدفوع", "money"), ("outstanding", "المتبقي للمورد", "money")]
    rows = []
    q = select(PurchaseInvoice, Supplier.name).join(Supplier, Supplier.id == PurchaseInvoice.supplier_id).where(PurchaseInvoice.invoice_date >= c.a, PurchaseInvoice.invoice_date <= c.b) \
        .order_by(PurchaseInvoice.number)
    for inv_, sname in c.db.execute(q):
        mny = pur.money(c.db, inv_)
        rows.append({"number": str(inv_.number), "supplier": sname, "supplier_no": inv_.supplier_invoice_no, "date": inv_.invoice_date.isoformat(), "status": inv_.status,
                     "receipt": inv_.receipt_status, "payment": mny["payment_status"], "total": m(inv_.total), "paid": m(mny["paid"]),
                     "outstanding": m(mny["outstanding"] if inv_.status == "posted" else 0)})
    return cols, rows


def r_supplier_balances(c):
    cols = [("supplier", "المورد", "text"), ("invoiced", "الفواتير المرحّلة", "money"), ("paid", "المدفوع", "money"), ("credits", "إشعارات دائنة", "money"), ("outstanding", "المتبقي للمورد", "money")]
    return cols, [{"supplier": r["supplier"], "invoiced": m(r["invoiced"]), "paid": m(r["paid"]), "credits": m(r["credits"]), "outstanding": m(r["outstanding"])} for r in pur.supplier_balances(c.db)]


def r_supplier_payments(c):
    cols = [("date", "التاريخ", "text"), ("supplier", "المورد", "text"), ("invoice", "فاتورة المورد", "text"), ("method", "الطريقة", "text"), ("reference", "المرجع", "text"), ("amount", "المبلغ", "money")]
    rows = []
    q = select(SupplierPayment, Supplier.name, PurchaseInvoice.supplier_invoice_no).join(Supplier, Supplier.id == SupplierPayment.supplier_id) \
        .join(PurchaseInvoice, PurchaseInvoice.id == SupplierPayment.invoice_id).where(SupplierPayment.paid_at >= c.start, SupplierPayment.paid_at < c.end).order_by(SupplierPayment.id)
    for p, sname, no in c.db.execute(q):
        rows.append({"date": _local(p.paid_at), "supplier": sname, "invoice": no, "method": p.method, "reference": p.reference, "amount": m(p.amount)})
    return cols, rows


# ---- workshop financial performance --------------------------------------------------------------------------------------------------
SOURCE_LABEL = {"direct": "شراء مباشر", "warehouse": "من المخزن", "customer": "من العميل"}


def r_job_parts(c):
    cols = [("job_no", "أمر", "text"), ("plate", "اللوحة", "text"), ("source", "المصدر", "text"), ("part", "القطعة", "text"), ("sku", "كود الصنف", "text"), ("qty", "الكمية", "text"),
            ("status", "الحالة", "text"), ("price", "الإيراد", "money")]
    show_cost = "parts.costs" in c.user.permissions
    if show_cost:
        cols += [("cost", "التكلفة", "money"), ("profit", "الربح", "money")]
    rows = []
    q = select(PartPurchase, VehicleVisit.visit_no, Vehicle.plate).join(VehicleVisit, VehicleVisit.id == PartPurchase.visit_id).join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id) \
        .where(VehicleVisit.arrival_at >= c.start, VehicleVisit.arrival_at < c.end, PartPurchase.status != "cancelled").order_by(VehicleVisit.visit_no, PartPurchase.id)
    from app.services.pricing import line_cost, line_price, returned_map
    ret = returned_map(c.db)
    for p, no, plate in c.db.execute(q):
        price, cost = line_price(c.db, p, ret), line_cost(c.db, p, ret)
        r = {"job_no": str(no), "plate": plate, "source": SOURCE_LABEL.get(p.source, p.source), "part": p.part_name, "sku": p.part_number, "qty": n(p.quantity),
             "status": p.status, "price": m(price)}
        if show_cost:
            r.update(cost=m(cost), profit=m(price - cost))
        rows.append(r)
    return cols, rows


def r_parts_profit_by_source(c):
    cols = [("source", "المصدر", "text"), ("revenue", "إيراد القطع", "money"), ("cogs", "تكلفة القطع", "money"), ("profit", "مجمل ربح القطع", "money")]
    cost = {"direct": ZERO, "warehouse": ZERO, "customer": ZERO}
    rev = {"direct": ZERO, "warehouse": ZERO, "customer": ZERO}
    q = select(InvoiceItem, PartPurchase).join(PartPurchase, PartPurchase.id == InvoiceItem.part_id).join(Invoice, Invoice.id == InvoiceItem.invoice_id) \
        .where(Invoice.status == "issued", Invoice.issued_at >= c.start, Invoice.issued_at < c.end)
    for item, part in c.db.execute(q):
        rev[part.source] += Decimal(item.amount)
        cost[part.source] += to_money(Decimal(item.quantity) * Decimal(part.unit_cost))
    returned = cogs_returned_in_period(c.db, c.start, c.end, by_source=True)
    rows = []
    for src in ("warehouse", "direct", "customer"):
        net_cost = cost[src] - returned[src]
        rows.append({"source": SOURCE_LABEL[src], "revenue": m(rev[src]), "cogs": m(net_cost), "profit": m(rev[src] - net_cost)})
    return cols, rows


REPORTS = {
    "inventory-stock": ("الأرصدة الحالية للمخزون", "inventory.read", r_stock),
    "inventory-valuation": ("تقييم المخزون", "inventory.costs", r_valuation),
    "low-stock": ("أصناف أوشكت على النفاد", "inventory.read", r_low_stock),
    "out-of-stock": ("أصناف نفدت", "inventory.read", r_out_of_stock),
    "stock-movements": ("حركة المخزون", "inventory.read", r_movements),
    "inventory-adjustments": ("تسويات وجرد المخزون", "inventory.read", r_adjustments),
    "fast-moving": ("الأصناف الأسرع حركة", "inventory.read", r_fast_moving),
    "slow-moving": ("الأصناف بطيئة الحركة", "inventory.read", r_slow_moving),
    "purchases-by-supplier": ("المشتريات حسب المورد", "purchasing.read", r_purchases_by_supplier),
    "supplier-invoices": ("سجل فواتير الموردين", "purchasing.read", r_supplier_invoices),
    "supplier-balances": ("أرصدة الموردين المستحقة", "purchasing.read", r_supplier_balances),
    "supplier-payments": ("مدفوعات الموردين (نقدي)", "purchasing.read", r_supplier_payments),
    "job-parts-consumption": ("استهلاك القطع حسب أمر الإصلاح", "visits.read", r_job_parts),
    "parts-profit-by-source": ("ربح القطع حسب المصدر (مخزن، شراء مباشر، عميل)", "reports.financial", r_parts_profit_by_source),  # no "/" : Excel sheet names forbid it
}

LABELS_EN = {
    "الأرصدة الحالية للمخزون": "Current stock balances", "تقييم المخزون": "Inventory valuation", "أصناف أوشكت على النفاد": "Low-stock items", "أصناف نفدت": "Out-of-stock items",
    "حركة المخزون": "Stock movement history", "تسويات وجرد المخزون": "Stock adjustments and counts", "الأصناف الأسرع حركة": "Fast-moving parts",
    "الأصناف بطيئة الحركة": "Slow-moving parts", "المشتريات حسب المورد": "Purchases by supplier", "سجل فواتير الموردين": "Supplier invoice register",
    "أرصدة الموردين المستحقة": "Supplier outstanding balances", "مدفوعات الموردين (نقدي)": "Supplier payments (cash basis)",
    "استهلاك القطع حسب أمر الإصلاح": "Parts consumption by repair order", "ربح القطع حسب المصدر (مخزن، شراء مباشر، عميل)": "Parts profit by source (warehouse, direct, customer)",
    "كود الصنف": "SKU", "الصنف": "Item", "المخزن": "Warehouse", "الرصيد": "On hand", "المحجوز": "Reserved", "المتاح": "Available", "الحد الأدنى": "Minimum stock",
    "متوسط التكلفة": "Average cost", "قيمة المخزون": "Inventory value", "الكمية": "Quantity", "كمية إعادة الطلب": "Reorder quantity", "المقترح طلبه": "Suggested order",
    "مكان التخزين": "Storage location", "النوع": "Type", "تغيّر المحجوز": "Reserved change", "الرصيد بعد": "Balance after", "المستند": "Document", "المستخدم": "User",
    "السبب": "Reason", "تكلفة الوحدة": "Unit cost", "القيمة": "Value", "رقم المستند": "Document no.", "رصيد النظام": "System qty", "المعدود": "Counted", "الفرق": "Difference",
    "قيمة الفرق": "Difference value", "المصروف في الفترة": "Issued in period", "الرصيد الحالي": "Current stock", "آخر صرف": "Last issue",
    "المورد": "Supplier", "عدد الفواتير": "Invoices", "المشتريات (بدون ضريبة)": "Purchases (excl. tax)", "الضريبة": "Tax", "الإجمالي": "Total",
    "رقم الفاتورة الداخلي": "Internal no.", "رقم فاتورة المورد": "Supplier invoice no.", "التاريخ": "Date", "الحالة": "Status", "الاستلام": "Receipt", "السداد": "Payment",
    "المدفوع": "Paid", "المتبقي للمورد": "Owed to supplier", "الفواتير المرحّلة": "Posted invoices", "إشعارات دائنة": "Credit notes", "فاتورة المورد": "Supplier invoice",
    "الطريقة": "Method", "المرجع": "Reference", "المبلغ": "Amount", "أمر": "Job", "اللوحة": "Plate", "المصدر": "Source", "القطعة": "Part", "الإيراد": "Revenue",
    "التكلفة": "Cost", "الربح": "Profit", "إيراد القطع": "Parts revenue", "تكلفة القطع": "Parts cost (COGS)", "مجمل ربح القطع": "Parts gross profit",
    "شراء مباشر": "Direct purchase", "من المخزن": "From warehouse", "من العميل": "Customer supplied",
}
