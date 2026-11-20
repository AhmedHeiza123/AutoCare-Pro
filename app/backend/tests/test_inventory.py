"""Inventory & purchasing module tests (real PostgreSQL, throw-away database; see tests/_harness.py).

Each test is named after the acceptance scenario / business example of the specification it verifies."""
import threading
import unittest
import uuid
from datetime import date
from decimal import Decimal

from tests._harness import D, ENABLED, FinanceCase, REQ, TEST_URL

if ENABLED:
    from sqlalchemy import create_engine, func, select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError

    from app.api import billing, inventory as api, inventory_jobs, jobs as jobs_api, parts, quotes
    from app.api.deps import require
    from app.core.errors import AppError
    from app.db import SessionLocal
    from app.models import (InventoryBalance, PartPurchase, Role, StockMovement, StockReservation, Supplier, Warehouse)
    from app.models.auth import User
    from app.services import inventory as svc


class InventoryCase(FinanceCase):
    """Builders that go through the real API functions."""

    def setUp(self):
        super().setUp()
        self.wh = self.db.scalar(select(Warehouse).where(Warehouse.is_default))

    def make_item(self, sku="FLT-001", name="Oil filter", price="50", **kw):
        body = api.ItemIn(sku=sku, name_en=name, selling_price=D(str(price)), **{k: (D(str(v)) if k in ("min_stock", "reorder_qty") else v) for k, v in kw.items()})
        out = api.create_item(body, REQ, user=self.user, db=self.db)
        self.db.commit()
        return out

    def make_supplier(self, name="Gulf Parts"):
        s = Supplier(name=name)
        self.db.add(s)
        self.db.commit()
        return s

    def purchase(self, supplier, lines, *, discount="0", tax="0", number=None, post=True, receive=True):
        self._n += 1
        body = api.PurchaseInvoiceIn(supplier_id=supplier.id, supplier_invoice_no=number or f"SUP-{self._n}", invoice_date=date.today(), discount=D(str(discount)),
                                     tax_rate=D(str(tax)), lines=[api.PLine(item_id=i, qty=D(str(q)), unit_cost=D(str(c))) for i, q, c in lines])
        inv = api.create_purchase_invoice(body, REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        if post:
            inv = api.post_purchase_invoice(uuid.UUID(inv["id"]), REQ, user=self.user, db=self.db)
            self.db.commit()
        if receive:
            self.receive(inv, {l["id"]: l["qty_ordered"] for l in inv["lines"]})
            inv = api.get_purchase_invoice(uuid.UUID(inv["id"]), _=self.user, db=self.db)
        return inv

    def receive(self, inv, qty_by_line, key=None):
        body = api.ReceiptIn(lines=[api.ReceiptLineIn(invoice_line_id=lid, qty=D(str(q))) for lid, q in qty_by_line.items()])
        out = api.receive(uuid.UUID(inv["id"]), body, REQ, idempotency_key=key, user=self.user, db=self.db)
        self.db.commit()
        return out

    def bal(self, item_id, warehouse_id=None):
        """The balance row; before the first posting there is none, which reads as an empty shelf."""
        from types import SimpleNamespace
        self.db.expire_all()
        row = self.db.get(InventoryBalance, (item_id, warehouse_id or self.wh.id))
        return row or SimpleNamespace(on_hand=D("0"), reserved=D("0"), value=D("0"), available=D("0"), avg_cost=D("0"))

    def wpart(self, job, item_id, qty, price=None):
        body = inventory_jobs.WarehousePartIn(item_id=item_id, quantity=D(str(qty)), unit_price=None if price is None else D(str(price)))
        out = inventory_jobs.add_warehouse_part(job.id, body, REQ, user=self.user, db=self.db)
        self.db.commit()
        return out

    def status(self, part_id, status):
        out = parts.part_status(part_id, parts.PartStatusIn(status=status), REQ, user=self.user, db=self.db)
        self.db.commit()
        return out

    def movements(self, **where):
        self.db.expire_all()
        q = select(StockMovement).order_by(StockMovement.id)
        for k, v in where.items():
            q = q.where(getattr(StockMovement, k) == v)
        return list(self.db.scalars(q))

    def user_with_role(self, role):
        r = self.db.scalar(select(Role).where(Role.name == role))
        u = User(username=f"u_{role}", full_name=role, password_hash="x", role_id=r.id)
        self.db.add(u)
        self.db.commit()
        return u


# ================================================================================================================ master data
class CatalogTests(InventoryCase):
    def test_01_create_item_and_block_duplicates(self):
        item = self.make_item("BRK-PAD-01", "Brake pads", brand="Bosch", mfr_part_no="0986AB1234", barcode="6291234567890")
        self.assertEqual((item["sku"], D(item["on_hand"]), D(item["available"])), ("BRK-PAD-01", D("0"), D("0")))
        for kw, code in (({"sku": "brk-pad-01", "name": "Brake pads again"}, "duplicate_sku"),                      # SKU is unique, case-insensitively
                         ({"sku": "BRK-PAD-02", "name": "Other pads", "barcode": "6291234567890"}, "duplicate_barcode"),
                         ({"sku": "BRK-PAD-03", "name": "Same part", "brand": "bosch", "mfr_part_no": "0986ab1234"}, "duplicate_part")):
            with self.assertRaises(AppError) as ctx:
                self.make_item(kw.pop("sku"), kw.pop("name"), **kw)
            self.db.rollback()
            self.assertEqual(ctx.exception.code, code)

    def test_default_warehouse_and_categories(self):
        wh = api.list_warehouses(_=self.user, db=self.db)
        self.assertEqual([w["code"] for w in wh], ["MAIN"])
        self.assertEqual(wh[0]["name_ar"], "المخزن الرئيسي للورشة")
        cat = api.create_category(api.CategoryIn(name_en="Brakes", name_ar="فرامل"), REQ, user=self.user, db=self.db)
        sub = api.create_category(api.CategoryIn(name_en="Brake pads", name_ar="تيل فرامل", parent_id=cat["id"]), REQ, user=self.user, db=self.db)
        self.db.commit()
        item = self.make_item("BRK-PAD-09", "Pads", category_id=cat["id"], subcategory_id=sub["id"])
        self.assertEqual(item["subcategory"]["name_en"], "Brake pads")
        with self.assertRaises(AppError):  # a sub-category of another parent is refused
            other = api.create_category(api.CategoryIn(name_en="Oils", name_ar="زيوت"), REQ, user=self.user, db=self.db)
            self.db.commit()
            self.make_item("X-1", "Wrong sub-category", category_id=other["id"], subcategory_id=sub["id"])
        self.db.rollback()


# ================================================================================================================ purchasing
class PurchasingTests(InventoryCase):
    def test_02_03_one_invoice_several_items_then_receive(self):
        sup, a, b = self.make_supplier(), self.make_item("A-1", "Filter A"), self.make_item("B-1", "Filter B")
        inv = self.purchase(sup, [(a["id"], 20, 30), (b["id"], 5, 100)], receive=False, tax="5")
        self.assertEqual((inv["subtotal"], inv["tax_amount"], inv["total"], inv["status"], inv["receipt_status"]), ("1100.00", "55.00", "1155.00", "posted", "none"))
        self.assertEqual(self.bal(a["id"]).on_hand, 0)  # posting the invoice does NOT create stock
        self.receive(inv, {l["id"]: l["qty_ordered"] for l in inv["lines"]})
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value, self.bal(b["id"]).value), (D("20"), D("600"), D("500")))
        done = api.get_purchase_invoice(uuid.UUID(inv["id"]), _=self.user, db=self.db)
        self.assertEqual((done["receipt_status"], done["payment_status"], done["outstanding"]), ("full", "unpaid", "1155.00"))

    def test_04_partial_receipts_are_exact_and_cannot_over_receive(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        inv = self.purchase(sup, [(a["id"], 3, "33.33")], discount="10", receive=False)  # line 99.99, invoice discount 10 -> 89.99 net
        line = inv["lines"][0]["id"]
        self.receive(inv, {line: 1})
        mid = api.get_purchase_invoice(uuid.UUID(inv["id"]), _=self.user, db=self.db)
        self.assertEqual((mid["receipt_status"], D(mid["lines"][0]["qty_open"])), ("partial", D("2")))
        with self.assertRaises(AppError) as ctx:
            self.receive(inv, {line: 3})
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "over_receipt")
        self.receive(inv, {line: 1})
        self.receive(inv, {line: 1})
        self.assertEqual(self.bal(a["id"]).value, D("89.99"))  # the three partial receipts add up to the exact net value
        self.assertEqual(api.get_purchase_invoice(uuid.UUID(inv["id"]), _=self.user, db=self.db)["receipt_status"], "full")

    def test_11_duplicate_receipt_key_and_duplicate_supplier_invoice(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        inv = self.purchase(sup, [(a["id"], 10, 20)], receive=False, number="INV-77")
        line = inv["lines"][0]["id"]
        first = self.receive(inv, {line: 4}, key="grn-1")
        replay = self.receive(inv, {line: 4}, key="grn-1")  # the same request sent again (double click / retry)
        self.assertEqual(first["id"], replay["id"])
        self.assertEqual(self.bal(a["id"]).on_hand, D("4"))
        with self.assertRaises(AppError) as ctx:
            self.purchase(sup, [(a["id"], 1, 1)], number="inv-77", receive=False)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "duplicate_supplier_invoice")

    def test_15_supplier_balance_is_independent_from_receipts(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        inv = self.purchase(sup, [(a["id"], 20, 30)], receive=False)  # we owe 600 although nothing arrived yet
        self.assertEqual(api.supplier_balances(_=self.user, db=self.db)[0]["outstanding"], "600.00")
        pay = api.pay_supplier(uuid.UUID(inv["id"]), api.SupplierPaymentIn(amount=D("250"), method="cash"), REQ, idempotency_key="pay-1", user=self.user, db=self.db)
        api.pay_supplier(uuid.UUID(inv["id"]), api.SupplierPaymentIn(amount=D("250"), method="cash"), REQ, idempotency_key="pay-1", user=self.user, db=self.db)  # replay
        self.db.commit()
        self.assertEqual(pay["invoice"]["outstanding"], "350.00")
        self.assertEqual(self.bal(a["id"]).on_hand, 0)  # paying does not create stock either
        with self.assertRaises(AppError) as ctx:
            api.pay_supplier(uuid.UUID(inv["id"]), api.SupplierPaymentIn(amount=D("400"), method="cash"), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "overpayment")
        api.pay_supplier(uuid.UUID(inv["id"]), api.SupplierPaymentIn(amount=D("350"), method="cash"), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        done = api.get_purchase_invoice(uuid.UUID(inv["id"]), _=self.user, db=self.db)
        self.assertEqual((done["payment_status"], done["outstanding"], done["receipt_status"]), ("paid", "0.00", "none"))

    def test_posted_invoice_and_receipts_can_be_reversed_only_while_stock_is_untouched(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A", price=50)
        inv = self.purchase(sup, [(a["id"], 10, 30)])
        rid = api.list_receipts(invoice_id=uuid.UUID(inv["id"]), limit=10, offset=0, _=self.user, db=self.db)[0]["id"]
        job = self.new_job()
        part = self.wpart(job, a["id"], 4)
        self.status(part["id"], "received")  # 4 units leave the shelf
        with self.assertRaises(AppError) as ctx:  # 6 left, the receipt was 10: cannot be undone
            api.reverse_receipt(uuid.UUID(rid), api.ReasonIn(reason="wrong supplier"), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "stock_already_used")
        # a fresh, untouched receipt reverses cleanly and the invoice can then be cancelled
        inv2 = self.purchase(sup, [(a["id"], 5, 40)])
        rid2 = api.list_receipts(invoice_id=uuid.UUID(inv2["id"]), limit=10, offset=0, _=self.user, db=self.db)[0]["id"]
        with self.assertRaises(AppError) as ctx2:
            api.cancel_purchase_invoice(uuid.UUID(inv2["id"]), api.ReasonIn(reason="mistake"), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx2.exception.code, "has_receipts")
        api.reverse_receipt(uuid.UUID(rid2), api.ReasonIn(reason="wrong supplier"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(self.bal(a["id"]).on_hand, D("6"))
        self.assertEqual(self.bal(a["id"]).value, D("180"))  # 6 units still valued at 30 each
        out = api.cancel_purchase_invoice(uuid.UUID(inv2["id"]), api.ReasonIn(reason="mistake"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(out["status"], "cancelled")


# ================================================================================================================ valuation & ledger
class ValuationTests(InventoryCase):
    def test_13_weighted_average_cost_and_value(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        self.purchase(sup, [(a["id"], 10, 100)])
        self.purchase(sup, [(a["id"], 10, 120)])
        b = self.bal(a["id"])
        self.assertEqual((b.on_hand, b.value, b.avg_cost), (D("20"), D("2200"), D("110")))
        job = self.new_job()
        part = self.wpart(job, a["id"], 5)
        self.status(part["id"], "received")
        b = self.bal(a["id"])
        self.assertEqual((b.on_hand, b.value, b.avg_cost), (D("15"), D("1650"), D("110")))  # 5 issued at 110 -> 550 out
        issue = self.movements(movement_type="ISSUE")[0]
        self.assertEqual((issue.qty, issue.unit_cost, issue.value_delta), (D("-5"), D("110"), D("-550")))

    def test_ledger_is_append_only_and_the_database_refuses_overselling(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        self.purchase(sup, [(a["id"], 5, 10)])
        for sql in ("UPDATE stock_movements SET qty = 99", "DELETE FROM stock_movements",
                    f"UPDATE inventory_balances SET reserved = on_hand + 1 WHERE item_id = {a['id']}",
                    f"UPDATE inventory_balances SET on_hand = -1 WHERE item_id = {a['id']}"):
            with self.assertRaises(DBAPIError, msg=sql):
                self.db.execute(text(sql))
            self.db.rollback()
        inv = self.purchase(sup, [(a["id"], 1, 10)], receive=False)
        with self.assertRaises(DBAPIError):  # a posted purchase invoice is immutable
            self.db.execute(text(f"UPDATE purchase_invoices SET total = 1 WHERE id = '{inv['id']}'"))
        self.db.rollback()

    def test_adjustment_count_transfer_and_reversal(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        self.purchase(sup, [(a["id"], 10, 20)])
        api.create_adjustment(api.AdjustmentIn(reason="damaged in storage", lines=[api.AdjLine(item_id=a["id"], qty_delta=D("-2"))]), REQ, idempotency_key="adj-1", user=self.user, db=self.db)
        api.create_adjustment(api.AdjustmentIn(reason="damaged in storage", lines=[api.AdjLine(item_id=a["id"], qty_delta=D("-2"))]), REQ, idempotency_key="adj-1", user=self.user, db=self.db)  # replay
        self.db.commit()
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("8"), D("160")))
        count = api.create_count(api.CountIn(lines=[api.CountLine(item_id=a["id"], counted_qty=D("9"))]), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(D(count["lines"][0]["qty_delta"]), D("1"))
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("9"), D("180")))  # the found unit is valued at the average cost
        mid = [m for m in self.movements(movement_type="COUNT")][0].id
        api.reverse(mid, api.ReasonIn(reason="recount was wrong"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(self.bal(a["id"]).on_hand, D("8"))
        with self.assertRaises(AppError) as ctx:  # one reversal only
            api.reverse(mid, api.ReasonIn(reason="again"), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "already_reversed")
        second = Warehouse(code="BR2", name_en="Branch", name_ar="فرع", is_default=False)
        self.db.add(second)
        self.db.commit()
        doc = api.create_transfer(api.TransferIn(from_warehouse_id=self.wh.id, to_warehouse_id=second.id, lines=[api.TransferLine(item_id=a["id"], qty=D("3"))]),
                                  REQ, idempotency_key="tr-1", user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(len(doc["movements"]), 2)
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("5"), D("100")))
        self.assertEqual((self.bal(a["id"], second.id).on_hand, self.bal(a["id"], second.id).value), (D("3"), D("60")))

    def test_opening_balance_once_and_supplier_return_with_credit(self):
        sup, a = self.make_supplier(), self.make_item("A-1", "Filter A")
        api.opening(api.OpeningIn(item_id=a["id"], qty=D("10"), unit_cost=D("25")), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        with self.assertRaises(AppError) as ctx:
            api.opening(api.OpeningIn(item_id=a["id"], qty=D("5"), unit_cost=D("25")), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "opening_exists")
        inv = self.purchase(sup, [(a["id"], 10, 35)])  # stock 20, value 600 -> average 30
        api.supplier_return(api.SupplierReturnIn(item_id=a["id"], qty=D("2"), supplier_id=sup.id, credit_amount=D("70"), invoice_id=uuid.UUID(inv["id"]), reason="wrong model"),
                            REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("18"), D("540")))
        self.assertEqual(api.get_purchase_invoice(uuid.UUID(inv["id"]), _=self.user, db=self.db)["outstanding"], "280.00")  # 350 - 70 credit


# ================================================================================================================ repair-order integration
class RepairOrderTests(InventoryCase):
    def _stock(self, qty=20, cost=30, price=50):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter", price=price)
        self.purchase(sup, [(a["id"], qty, cost)])
        return sup, a

    def test_05_no_deduction_for_a_quotation_reserve_on_approval_issue_when_taken(self):
        _, a = self._stock()
        job = self.new_job()
        part = self.wpart(job, a["id"], 2)
        self.assertEqual((part["source"], part["status"], D(part["unit_price"])), ("warehouse", "requested", D("50")))
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).reserved), (D("20"), D("0")))  # adding the part touches no stock
        quote = quotes.create_quote(job.id, quotes.QuoteCreate(from_job=True), REQ, user=self.user, db=self.db)
        self.db.commit()
        quotes.send_quote(quote["id"], REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(self.bal(a["id"]).reserved, D("0"))  # a quotation neither deducts nor reserves
        out = quotes.record_approval(quote["id"], quotes.ApprovalIn(decision="approved", method="in_person", evidence="customer ok"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertNotIn("stock_warnings", out)
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).reserved, self.bal(a["id"]).available), (D("20"), D("2"), D("18")))  # approval reserves
        self.status(part["id"], "received")  # taken from the shelf
        b = self.bal(a["id"])
        self.assertEqual((b.on_hand, b.reserved, b.value), (D("18"), D("0"), D("540")))
        row = self.db.get(PartPurchase, part["id"])
        self.assertEqual((row.issued_qty, row.unit_cost), (D("2"), D("30")))  # the job remembers the cost it was issued at
        self.assertEqual(self.db.scalar(select(StockReservation.status).where(StockReservation.part_id == part["id"])), "consumed")

    def test_06_rejected_quotation_releases_the_reservation(self):
        _, a = self._stock()
        job = self.new_job()
        part = self.wpart(job, a["id"], 3)
        self.status(part["id"], "ordered")  # reserved (no quotation yet, so no approval gate)
        self.assertEqual(self.bal(a["id"]).reserved, D("3"))
        quote = quotes.create_quote(job.id, quotes.QuoteCreate(from_job=True), REQ, user=self.user, db=self.db)
        self.db.commit()
        quotes.send_quote(quote["id"], REQ, user=self.user, db=self.db)
        self.db.commit()
        quotes.record_approval(quote["id"], quotes.ApprovalIn(decision="rejected", method="phone", evidence="too expensive"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).reserved, self.bal(a["id"]).available), (D("20"), D("0"), D("20")))
        self.assertEqual([m.movement_type for m in self.movements(movement_type="RELEASE")], ["RELEASE"])

    def test_cancelled_job_releases_stock_but_not_while_parts_are_issued(self):
        _, a = self._stock()
        job = self.new_job()
        p1, p2 = self.wpart(job, a["id"], 2), self.wpart(job, a["id"], 1)
        self.status(p1["id"], "ordered")
        self.status(p2["id"], "received")  # issued, not installed
        with self.assertRaises(AppError) as ctx:
            jobs_api.change_status(job.id, jobs_api.StatusIn(status="cancelled", reason="customer left"), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "stock_issued")
        inventory_ret = inventory_jobs.return_to_warehouse(p2["id"], inventory_jobs.WarehouseReturnIn(quantity=D("1"), reason="job cancelled"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(inventory_ret["part"]["status"], "returned")
        jobs_api.change_status(job.id, jobs_api.StatusIn(status="cancelled", reason="customer left"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).reserved), (D("20"), D("0")))

    def test_insufficient_stock_is_refused_everywhere(self):
        _, a = self._stock(qty=3)
        job = self.new_job()
        with self.assertRaises(AppError) as ctx:
            self.wpart(job, a["id"], 4)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "insufficient_stock")
        p = self.wpart(job, a["id"], 3)
        self.status(p["id"], "ordered")
        other = self.new_job()
        with self.assertRaises(AppError):  # the 3 units are reserved for the first job: nothing is available for the second
            self.wpart(other, a["id"], 1)
        self.db.rollback()

    def test_example_2_using_warehouse_stock_revenue_cogs_profit(self):
        _, a = self._stock(20, 30, 50)
        job = self.new_job()
        part = self.wpart(job, a["id"], 2)
        self.status(part["id"], "received")
        self.invoice(job)
        s = self.summary()
        self.assertEqual((s["parts_revenue_warehouse"], s["cogs_warehouse"], s["parts_net"], s["direct_costs_parts"], s["gross_profit"]),
                         (D("100.00"), D("60.00"), D("100.00"), D("60.00"), D("40.00")))
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("18"), D("540")))
        self.assertEqual(s["inventory_asset_value"], D("540.00"))
        row = self.report("job-profit")["rows"][0]
        self.assertEqual((row["revenue"], row["cost"], row["profit"]), ("100.00", "60.00", "40.00"))

    def test_example_1_buying_stock_is_not_an_expense(self):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter")
        inv = self.purchase(sup, [(a["id"], 20, 30)])
        s = self.summary()
        self.assertEqual((s["inventory_purchases"], s["inventory_received_value"], s["inventory_asset_value"], s["supplier_outstanding"]),
                         (D("600.00"), D("600.00"), D("600.00"), D("600.00")))
        self.assertEqual((s["operating_expenses"], s["gross_profit"], s["estimated_net_profit"], s["direct_costs_parts"]), (D("0.00"),) * 4)
        api.pay_supplier(uuid.UUID(inv["id"]), api.SupplierPaymentIn(amount=D("600"), method="cash"), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        s = self.summary()
        self.assertEqual((s["supplier_payments"], s["supplier_outstanding"], s["inventory_asset_value"]), (D("600.00"), D("0.00"), D("600.00")))
        self.assertEqual((s["operating_expenses"], s["estimated_net_profit"]), (D("0.00"), D("0.00")))  # paying the supplier is still not an expense
        self.assertEqual(s["net_cash_flow"], D("-600.00"))  # ... but it IS cash going out (cash view only)

    def test_07_example_3_customer_supplied_part(self):
        _, a = self._stock()
        job = self.new_job()
        before = len(self.movements())
        part = inventory_jobs.add_customer_part(job.id, inventory_jobs.CustomerPartIn(description="Oil filter", quantity=D("1")), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual((part["source"], D(part["unit_price"]), part["status"], part["warranty_months"]), ("customer", D("0"), "received", None))
        self.add_labor(job, 40, "Install oil filter")
        inv = self.invoice(job)
        self.assertEqual(inv["total"], "40.00")  # installation labor only
        s = self.summary()
        self.assertEqual((s["labor_net"], s["parts_net"], s["parts_revenue_customer_supplied"], s["direct_costs_parts"]), (D("40.00"), D("0.00"), D("0.00"), D("0.00")))
        self.assertEqual(len(self.movements()), before)  # no warehouse movement at all
        self.assertEqual(self.bal(a["id"]).on_hand, D("20"))
        with self.assertRaises(AppError):  # a customer's part cannot be given a price or a cost
            parts.update_part(part["id"], parts.PartPatch(unit_price=D("20")), REQ, user=self.user, db=self.db)
        self.db.rollback()

    def test_08_example_4_direct_purchase_never_touches_the_warehouse(self):
        _, a = self._stock()
        moves = len(self.movements())
        job = self.new_job()
        self.add_part(job, 1, 90, 140)  # the original workflow
        self.invoice(job)
        s = self.summary()
        self.assertEqual((s["parts_revenue_direct"], s["cogs_direct"], s["gross_profit"], s["cogs_warehouse"]), (D("140.00"), D("90.00"), D("50.00"), D("0.00")))
        self.assertEqual(len(self.movements()), moves)
        self.assertEqual(self.db.get(PartPurchase, self.db.scalar(select(func.max(PartPurchase.id)))).source, "direct")

    def test_no_double_counting_when_warehouse_and_direct_parts_share_a_job(self):
        _, a = self._stock(20, 30, 50)
        job = self.new_job()
        w = self.wpart(job, a["id"], 2)
        self.status(w["id"], "received")
        self.add_part(job, 1, 90, 140)
        self.invoice(job)
        s = self.summary()
        self.assertEqual((s["cogs_warehouse"], s["cogs_direct"], s["direct_costs_parts"], s["gross_profit"]), (D("60.00"), D("90.00"), D("150.00"), D("90.00")))  # 240 - 150
        self.assertEqual(s["operating_expenses"], D("0.00"))

    def test_warehouse_part_is_billed_only_after_it_was_issued(self):
        _, a = self._stock()
        job = self.new_job()
        self.add_labor(job, 100)
        w = self.wpart(job, a["id"], 1)
        first = self.invoice(job, issue=False)
        self.assertEqual(first["subtotal"], "100.00")  # the part has not left the shelf: not billable yet, its cost is unknown
        billing.delete_draft_invoice(uuid.UUID(first["id"]), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.status(w["id"], "received")
        second = self.invoice(job, issue=False)
        self.assertEqual(second["subtotal"], "150.00")

    def test_09_10_returns_unused_goes_back_defective_does_not(self):
        _, a = self._stock(20, 30, 50)
        job = self.new_job()
        part = self.wpart(job, a["id"], 3)
        self.status(part["id"], "received")  # 3 issued at 30 each
        inv = self.invoice(job)
        s = self.summary()
        self.assertEqual((s["direct_costs_parts"], s["gross_profit"]), (D("90.00"), D("60.00")))
        r1 = inventory_jobs.return_to_warehouse(part["id"], inventory_jobs.WarehouseReturnIn(quantity=D("1"), disposition="unused", reason="not needed"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(r1["disposition"], "warehouse")
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("18"), D("540")))  # one unit is back, valued at the cost it left with
        r2 = inventory_jobs.return_to_warehouse(part["id"], inventory_jobs.WarehouseReturnIn(quantity=D("1"), disposition="defective", reason="cracked housing"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(r2["disposition"], "defective")
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("18"), D("540")))  # a defective part is NOT restocked
        self.credit(inv["id"], 100)  # the customer is credited for the two parts taken off the job
        s = self.summary()
        # COGS: 90 billed - 30 recovered by the unused return; the defective unit's 30 stays as a loss
        self.assertEqual((s["cogs_warehouse"], s["direct_costs_parts"]), (D("60.00"), D("60.00")))
        self.assertEqual(self.movements(movement_type="RETURN_TO_WAREHOUSE")[0].qty, D("1"))
        with self.assertRaises(AppError) as ctx:  # the supplier-return endpoint refuses warehouse parts
            parts.return_part(part["id"], parts.ReturnIn(quantity=D("1"), reason="return to supplier"), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "use_warehouse_return")

    def test_11_a_part_is_issued_once(self):
        _, a = self._stock()
        job = self.new_job()
        part = self.wpart(job, a["id"], 2)
        self.status(part["id"], "received")
        row = self.db.get(PartPurchase, part["id"])
        self.assertIsNone(svc.issue_for_part(self.db, row, self.user))  # calling the issue again deducts nothing
        self.db.commit()
        with self.assertRaises(AppError):  # nor can the status be replayed
            self.status(part["id"], "received")
        self.db.rollback()
        self.assertEqual((self.bal(a["id"]).on_hand, len(self.movements(movement_type="ISSUE"))), (D("18"), 1))

    def test_issued_quantity_cannot_be_changed_and_cost_comes_from_inventory(self):
        _, a = self._stock()
        job = self.new_job()
        part = self.wpart(job, a["id"], 2)
        out = parts.update_part(part["id"], parts.PartPatch(quantity=D("3")), REQ, user=self.user, db=self.db)  # before issue: fine
        self.db.commit()
        self.assertEqual(D(out["quantity"]), D("3"))
        with self.assertRaises(AppError) as ctx:
            parts.update_part(part["id"], parts.PartPatch(unit_cost=D("1")), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "cost_from_inventory")
        self.status(part["id"], "received")
        with self.assertRaises(AppError) as ctx2:
            parts.update_part(part["id"], parts.PartPatch(quantity=D("1")), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx2.exception.code, "already_issued")


# ================================================================================================================ concurrency
class ConcurrencyTests(InventoryCase):
    def _race(self, fns):
        barrier, results = threading.Barrier(len(fns)), [None] * len(fns)

        def worker(i, fn):
            db = SessionLocal()
            try:
                user = db.get(User, self.user.id)
                barrier.wait(timeout=20)
                try:
                    fn(db, user)
                    db.commit()
                    results[i] = "ok"
                except AppError as e:
                    db.rollback()
                    results[i] = e.code
            finally:
                db.close()

        threads = [threading.Thread(target=worker, args=(i, fn)) for i, fn in enumerate(fns)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        return results

    def test_12_two_requests_cannot_reserve_or_issue_the_last_unit(self):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter")
        self.purchase(sup, [(a["id"], 1, 30)])
        pa, pb = self.wpart(self.new_job(), a["id"], 1), self.wpart(self.new_job(), a["id"], 1)
        results = self._race([lambda db, u, p=p: parts.part_status(p["id"], parts.PartStatusIn(status="ordered"), REQ, user=u, db=db) for p in (pa, pb)])
        self.assertEqual(sorted(results), ["insufficient_stock", "ok"])
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).reserved), (D("1"), D("1")))

    def test_12_concurrent_issue_never_goes_negative(self):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter")
        self.purchase(sup, [(a["id"], 1, 30)])
        pa, pb = self.wpart(self.new_job(), a["id"], 1), self.wpart(self.new_job(), a["id"], 1)
        results = self._race([lambda db, u, p=p: parts.part_status(p["id"], parts.PartStatusIn(status="received"), REQ, user=u, db=db) for p in (pa, pb)])
        self.assertEqual(sorted(results), ["insufficient_stock", "ok"])
        self.assertEqual((self.bal(a["id"]).on_hand, self.bal(a["id"]).value), (D("0"), D("0")))
        self.assertEqual(len(self.movements(movement_type="ISSUE")), 1)

    def test_concurrent_identical_goods_receipts_post_once(self):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter")
        inv = self.purchase(sup, [(a["id"], 10, 30)], receive=False)
        line = inv["lines"][0]["id"]
        body = api.ReceiptIn(lines=[api.ReceiptLineIn(invoice_line_id=line, qty=D("10"))])
        results = self._race([lambda db, u: api.receive(uuid.UUID(inv["id"]), body, REQ, idempotency_key="same-key", user=u, db=db)] * 2)
        self.assertEqual(results.count("ok") + results.count("over_receipt"), 2)
        self.assertEqual(self.bal(a["id"]).on_hand, D("10"))  # received once, whatever the interleaving


# ================================================================================================================ reports, permissions
class ReportAndPermissionTests(InventoryCase):
    def test_inventory_reports_run_and_hide_costs_from_roles_without_the_permission(self):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter", min_stock=5)
        self.purchase(sup, [(a["id"], 6, 30)])
        job = self.new_job()
        w = self.wpart(job, a["id"], 2)
        self.status(w["id"], "received")
        self.invoice(job)
        from app.api.reports import REPORTS, run
        for name in ("inventory-stock", "inventory-valuation", "low-stock", "out-of-stock", "stock-movements", "inventory-adjustments", "fast-moving", "slow-moving",
                     "purchases-by-supplier", "supplier-invoices", "supplier-balances", "supplier-payments", "job-parts-consumption", "parts-profit-by-source"):
            self.assertIn(name, REPORTS)
            self.assertIn("rows", self.report(name), name)
        self.assertEqual(self.report("low-stock")["rows"][0]["sku"], "FLT-1")  # 4 left, minimum 5
        self.assertEqual(self.report("inventory-valuation")["totals"]["value"], "120.00")
        by_source = {r["source"]: r for r in self.report("parts-profit-by-source")["rows"]}
        self.assertEqual((by_source["من المخزن"]["revenue"], by_source["من المخزن"]["cogs"], by_source["من المخزن"]["profit"]), ("100.00", "60.00", "40.00"))
        tech = self.user_with_role("technician")
        keys = {c["key"] for c in run("inventory-stock", self.db, tech, None, None, {})["columns"]}
        self.assertNotIn("value", keys)
        self.assertNotIn("avg_cost", keys)

    def test_inventory_report_exports_in_both_languages(self):
        from app.api.reports import export

        class ExportRequest:
            client = None
            query_params: dict = {}

        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter", name_ar="فلتر زيت")
        self.purchase(sup, [(a["id"], 6, 30)])
        w = self.wpart(self.new_job(), a["id"], 2)
        self.status(w["id"], "received")
        for name in ("inventory-stock", "inventory-valuation", "stock-movements", "supplier-invoices", "supplier-balances", "job-parts-consumption", "parts-profit-by-source"):
            for fmt in ("csv", "xlsx"):
                for lang in ("ar", "en"):
                    resp = export(name, ExportRequest(), format=fmt, lang=lang, date_from=None, date_to=None, user=self.user, db=self.db)
                    self.db.commit()
                    self.assertGreater(len(resp.body), 80, (name, fmt, lang))
        header = export("inventory-valuation", ExportRequest(), format="csv", lang="en", date_from=None, date_to=None, user=self.user, db=self.db).body.decode("utf-8-sig").splitlines()[0]
        self.assertIn("Average cost", header)
        self.assertIn("Inventory value", header)

    def test_17_permissions(self):
        sup, a = self.make_supplier(), self.make_item("FLT-1", "Oil filter")
        self.purchase(sup, [(a["id"], 5, 30)])
        tech, acct, keeper = (self.user_with_role(r) for r in ("technician", "accountant", "storekeeper"))
        with self.assertRaises(AppError):  # a technician cannot adjust stock or post purchases
            require("inventory.adjust")(user=tech)
        with self.assertRaises(AppError):
            require("purchasing.write")(user=tech)
        with self.assertRaises(AppError):  # an accountant sees costs and pays suppliers but does not touch stock
            require("inventory.adjust")(user=acct)
        require("inventory.costs")(user=acct)
        require("purchasing.write")(user=acct)
        for perm in ("inventory.adjust", "inventory.write", "purchasing.write", "inventory.read"):
            require(perm)(user=keeper)
        with self.assertRaises(AppError):  # the storekeeper cannot see inventory value
            require("inventory.costs")(user=keeper)
        detail_tech = api.get_item_detail(a["id"], user=tech, db=self.db)
        detail_acct = api.get_item_detail(a["id"], user=acct, db=self.db)
        self.assertNotIn("avg_cost", detail_tech)
        self.assertNotIn("purchase_price", detail_tech)
        self.assertEqual((detail_acct["avg_cost"], detail_acct["stock_value"]), ("30.0000", "150.00"))

    def test_dashboard_numbers(self):
        sup, a, b = self.make_supplier(), self.make_item("A-1", "Item A", min_stock=10), self.make_item("B-1", "Item B")
        self.purchase(sup, [(a["id"], 6, 10)])
        d = api.dashboard(date_from=None, date_to=None, user=self.user, db=self.db)
        self.assertEqual((d["total_items"], D(d["total_stock_qty"]), d["low_stock_items"], d["out_of_stock_items"], d["inventory_value"], d["inventory_purchases"]),
                         (2, D("6"), 1, 1, "60.00", "60.00"))
        self.assertEqual(d["links"]["low_stock_items"], "/api/inventory/items?low_stock=true")
        low = api.list_items(low_stock=True, q=None, category_id=None, active=None, out_of_stock=False, in_stock=False, warehouse_id=None, limit=50, offset=0, user=self.user, db=self.db)
        self.assertEqual([i["sku"] for i in low["items"]], ["A-1"])


# ================================================================================================================ migration & backup
class MigrationAndBackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ENABLED:
            raise unittest.SkipTest("set AUTOCARE_TEST_DATABASE_URL to a database whose name contains 'test'")

    def _scratch_db(self):
        base = make_url(TEST_URL)
        name = f"autocare_test_scratch_{uuid.uuid4().hex[:8]}"
        admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as c:
            c.execute(text(f'CREATE DATABASE "{name}" ENCODING \'UTF8\' TEMPLATE template0'))
        self.addCleanup(self._drop, admin, name)
        return base.set(database=name), name

    @staticmethod
    def _drop(admin, name):
        with admin.connect() as c:
            c.execute(text("select pg_terminate_backend(pid) from pg_stat_activity where datname = :n and pid <> pg_backend_pid()"), {"n": name})
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()

    def _alembic(self, url, command_name, rev):
        import os
        from alembic import command
        from alembic.config import Config
        from tests._harness import BACKEND
        cfg = Config(str(BACKEND / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND / "alembic"))
        old = os.environ.get("AUTOCARE_MIGRATE_URL")
        os.environ["AUTOCARE_MIGRATE_URL"] = url.render_as_string(hide_password=False)
        try:
            getattr(command, command_name)(cfg, rev)
        finally:
            os.environ["AUTOCARE_MIGRATE_URL"] = old or TEST_URL

    def _insert(self, conn, meta, table, ids, **over):
        """Insert a minimal valid row into a table of the OLD schema (fills required columns, resolves foreign keys)."""
        import datetime as dt
        import sqlalchemy as sa
        t = meta.tables[table]
        vals = {}
        for col in t.columns:
            if col.name in over:
                vals[col.name] = over[col.name]
            elif col.nullable or col.server_default is not None or col.identity is not None:
                continue
            elif col.foreign_keys:
                vals[col.name] = ids[next(iter(col.foreign_keys)).column.table.name]
            elif isinstance(col.type, (sa.String, sa.Text)):
                vals[col.name] = "x"
            elif isinstance(col.type, (sa.Integer, sa.BigInteger)):
                vals[col.name] = 1
            elif isinstance(col.type, sa.Numeric):
                vals[col.name] = D("0")
            elif isinstance(col.type, sa.Boolean):
                vals[col.name] = True
            elif isinstance(col.type, sa.DateTime):
                vals[col.name] = dt.datetime.now(dt.timezone.utc)
            elif isinstance(col.type, sa.Date):
                vals[col.name] = dt.date.today()
            elif isinstance(col.type, sa.Uuid):
                vals[col.name] = uuid.uuid4()
            else:
                vals[col.name] = {}
        pk = t.primary_key.columns.values()[0]
        ids[table] = conn.execute(t.insert().values(**vals).returning(pk)).scalar()

    def test_18_upgrade_from_0010_keeps_existing_parts_and_downgrade_is_possible(self):
        import sqlalchemy as sa
        url, _ = self._scratch_db()
        self._alembic(url, "upgrade", "0010")
        eng = create_engine(url)
        meta, ids = sa.MetaData(), {}
        with eng.begin() as conn:
            meta.reflect(bind=conn)
            self.assertNotIn("inventory_items", meta.tables)
            for table, over in (("customers", {}), ("vehicles", {"current_customer_id": None}), ("vehicle_visits", {}),
                                ("part_purchases", {"unit_cost": D("12.34"), "unit_price": D("20.00"), "quantity": D("2.00"), "status": "installed"})):
                self._insert(conn, meta, table, ids, **over)
        self._alembic(url, "upgrade", "head")
        with eng.connect() as conn:
            row = conn.execute(text("select source, inventory_item_id, issued_qty, unit_cost, unit_price, quantity from part_purchases")).one()
            self.assertEqual((row.source, row.inventory_item_id, row.issued_qty, row.unit_cost, row.unit_price, row.quantity), ("direct", None, D("0"), D("12.34"), D("20.00"), D("2.00")))
            self.assertEqual(conn.execute(text("select code, is_default from warehouses")).all(), [("MAIN", True)])
            for table in ("inventory_items", "stock_movements", "inventory_balances", "purchase_invoices", "goods_receipts", "supplier_payments", "stock_adjustments"):
                self.assertEqual(conn.execute(text(f"select count(*) from {table}")).scalar(), 0, table)
            triggers = {r[0] for r in conn.execute(text("select tgname from pg_trigger where not tgisinternal"))}
            self.assertTrue({"stock_movements_no_change", "purchase_invoices_guard_trg", "purchase_invoice_lines_guard_trg", "supplier_payments_no_change"} <= triggers)
            self.assertEqual(conn.execute(text("select version_num from alembic_version")).scalar(), "0012")  # head (0011 inventory + 0012 extra roles)
        self._alembic(url, "downgrade", "0010")  # rollback path
        with eng.connect() as conn:
            self.assertEqual(conn.execute(text("select unit_cost from part_purchases")).scalar(), D("12.34"))
            self.assertIsNone(conn.execute(text("select to_regclass('inventory_items')")).scalar())
        self._alembic(url, "upgrade", "head")  # and forward again
        eng.dispose()

    def test_18_dump_and_restore_keep_the_inventory(self):
        """The backup mechanism (pg_dump / pg_restore, which the application's backup and restore use) carries every new table."""
        import tempfile
        from pathlib import Path
        from app.backup import pgtools
        class Scratch(InventoryCase):  # reuse the builders (fresh seeded database) outside a normal test method
            def runTest(self):
                pass

        case = Scratch()
        case.setUpClass()
        case.setUp()
        try:
            sup, a = case.make_supplier(), case.make_item("FLT-1", "Oil filter")
            case.purchase(sup, [(a["id"], 20, 30)])
            job = case.new_job()
            w = case.wpart(job, a["id"], 2)
            case.status(w["id"], "received")
            case.db.commit()
            tables = ["inventory_items", "inventory_balances", "stock_movements", "purchase_invoices", "purchase_invoice_lines", "goods_receipts", "goods_receipt_lines",
                      "part_purchases", "warehouses"]
            url = pgtools.db_url()
            with tempfile.TemporaryDirectory() as tmp:
                dump = Path(tmp) / "x.dump"
                pgtools.pg_dump(url, dump, None, ["backup_records"])
                restored = pgtools.temp_db_name("autocare_test_restore")
                pgtools.create_database(url, restored)
                try:
                    pgtools.pg_restore(url, dump, restored)
                    eng = create_engine(pgtools.with_database(url, restored))
                    with eng.connect() as conn, case.db.get_bind().connect() as live:
                        for t in tables:
                            self.assertEqual(conn.execute(text(f"select count(*) from {t}")).scalar(), live.execute(text(f"select count(*) from {t}")).scalar(), t)
                        self.assertEqual(conn.execute(text("select on_hand, value from inventory_balances")).one(), (D("18"), D("540")))
                        self.assertEqual(conn.execute(text("select version_num from alembic_version")).scalar(), "0012")
                        with self.assertRaises(DBAPIError):  # the guards travel with the dump
                            conn.execute(text("delete from stock_movements"))
                    eng.dispose()
                finally:
                    pgtools.drop_database(url, restored)
        finally:
            case.tearDown()


if __name__ == "__main__":
    unittest.main()
