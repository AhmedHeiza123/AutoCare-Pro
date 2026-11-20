"""Reporting-period consistency across months, and all-or-nothing behaviour of multi-line business transactions."""
import unittest
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from tests._harness import D, ENABLED, REQ
from tests.test_inventory import InventoryCase

if ENABLED:
    from sqlalchemy import func, select, text

    from app.api import finance, inventory as api, jobs as jobs_api
    from app.core.errors import AppError
    from app.models import CreditNote, Expense, Invoice, Payment, PurchaseInvoice, StockMovement, SupplierPayment


def at(y, m, d=15):
    return datetime(y, m, d, 10, 0, tzinfo=timezone.utc)


MONEY_KEYS = ("revenue_invoiced_ex_tax", "labor_billed", "parts_billed", "parts_cost_billed", "parts_cost_returned", "direct_costs_parts", "credit_notes",
              "net_revenue_ex_tax", "cash_received", "refunds_paid", "operating_expenses", "gross_profit", "estimated_net_profit", "tax_invoiced",
              "inventory_purchases", "supplier_payments", "discount_invoiced")


class PeriodTests(InventoryCase):
    def period(self, d1, d2):
        out = finance.financial_summary(date_from=d1, date_to=d2, _=self.user, db=self.db)
        return {k: D(str(out[k])) for k in MONEY_KEYS + ("inventory_asset_value", "supplier_outstanding", "receivables_outstanding")}

    def test_figures_split_across_months_add_up_to_the_whole_range(self):
        item = self.make_item("PER-001", "Period part", price="100")
        sup = self.make_supplier()
        # September: purchase 10 @ 40 (posted, received) and the supplier is paid 150 in October
        pi = self.purchase(sup, [(item["id"], 10, "40")])
        self.db.execute(text("update purchase_invoices set posted_at=:t"), {"t": at(2026, 9)})
        self.db.commit()
        api.pay_supplier(uuid.UUID(pi["id"]), api.SupplierPaymentIn(amount=D("150"), method="cash"), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        self.backdate("update supplier_payments set paid_at=:t", {"t": at(2026, 10, 3)})
        # October: job with 2 warehouse parts (cost 80) + labor 200, invoice 300 -> issued, paid 100
        j1 = self.new_job()
        self.add_labor(j1, 200)
        p1 = self.wpart(j1, item["id"], 2, price=50)
        self.status(p1["id"], "received")
        inv1 = self.invoice(j1)
        self.pay(inv1["id"], 100)
        # November: job with labor only, invoice 500, paid in full in December; credit note of 50 in December
        j2 = self.new_job()
        self.add_labor(j2, 500)
        inv2 = self.invoice(j2)
        self.pay(inv2["id"], 500)
        self.credit(inv2["id"], 50)
        self.db.execute(text("update invoices set issued_at=:t where id=:i"), {"t": at(2026, 10), "i": inv1["id"]})
        self.db.execute(text("update invoices set issued_at=:t where id=:i"), {"t": at(2026, 11), "i": inv2["id"]})
        self.db.execute(text("update payments set paid_at=:t where invoice_id=:i"), {"t": at(2026, 10, 20), "i": inv1["id"]})
        self.db.execute(text("update payments set paid_at=:t where invoice_id=:i"), {"t": at(2026, 12, 2), "i": inv2["id"]})
        self.db.execute(text("update credit_notes set created_at=:t"), {"t": at(2026, 12, 9)})
        self.db.commit()
        # an operating expense in November: purchases and supplier payments must not be counted as expenses
        cat = self.db.scalar(text("select id from expense_categories limit 1"))
        self.db.add(Expense(category_id=cat, amount=D("70"), expense_date=date(2026, 11, 5), description="rent", created_by=self.user.id))
        self.db.commit()

        months = {m: self.period(date(2026, m, 1), date(2026, m, 28 if m == 2 else 30 if m in (9, 11) else 31)) for m in (9, 10, 11, 12)}
        whole = self.period(date(2026, 9, 1), date(2026, 12, 31))
        for k in MONEY_KEYS:
            self.assertEqual(sum(months[m][k] for m in months), whole[k], f"{k}: the months do not add up to the whole period")
        # spot-check what belongs where
        self.assertEqual(months[9]["inventory_purchases"], D("400"))                                  # the purchase is September's, accrual
        self.assertEqual((months[9]["operating_expenses"], months[9]["gross_profit"]), (D("0"), D("0")))  # buying stock is not an expense
        self.assertEqual(months[10]["supplier_payments"], D("150"))
        self.assertEqual((months[10]["revenue_invoiced_ex_tax"], months[10]["parts_cost_billed"], months[10]["gross_profit"]), (D("300"), D("80"), D("220")))
        self.assertEqual((months[11]["revenue_invoiced_ex_tax"], months[11]["operating_expenses"], months[11]["credit_notes"]), (D("500"), D("70"), D("0")))
        self.assertEqual((months[12]["credit_notes"], months[12]["net_revenue_ex_tax"], months[12]["cash_received"]), (D("50"), D("-50"), D("500")))
        self.assertEqual(whole["gross_profit"], D("220") + D("500") - D("50"))
        self.assertEqual(whole["operating_expenses"], D("70"))
        # snapshots do not depend on the chosen range
        self.assertEqual(months[9]["inventory_asset_value"], whole["inventory_asset_value"])
        self.assertEqual(whole["inventory_asset_value"], D("320"))   # 8 units left @ 40
        self.assertEqual(whole["supplier_outstanding"], D("250"))     # 400 owed - 150 paid

    def test_returning_billed_parts_in_a_later_month_reduces_that_months_cogs_only(self):
        item = self.make_item("PER-002", "Return part", price="100")
        self.purchase(self.make_supplier(), [(item["id"], 5, "20")])
        job = self.new_job()
        part = self.wpart(job, item["id"], 2, price=60)
        self.status(part["id"], "received")
        inv = self.invoice(job)
        self.db.execute(text("update invoices set issued_at=:t where id=:i"), {"t": at(2026, 10), "i": inv["id"]})
        self.db.commit()
        from app.api import inventory_jobs
        inventory_jobs.return_to_warehouse(part["id"], inventory_jobs.WarehouseReturnIn(quantity=D("1"), disposition="unused", reason="not needed"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.db.execute(text("update part_returns set returned_at=:t"), {"t": at(2026, 11)})
        self.backdate("update stock_movements set ts=:t where movement_type='RETURN_TO_WAREHOUSE'", {"t": at(2026, 11)})
        self.db.commit()
        whole = self.period(date(2026, 10, 1), date(2026, 11, 30))
        oct_, nov = self.period(date(2026, 10, 1), date(2026, 10, 31)), self.period(date(2026, 11, 1), date(2026, 11, 30))
        for k in ("parts_cost_billed", "parts_cost_returned", "direct_costs_parts", "gross_profit"):
            self.assertEqual(oct_[k] + nov[k], whole[k], k)

    def backdate(self, sql, params):
        """The ledger and supplier payments are append-only (triggers); the throw-away test database may bypass them to date rows in the past."""
        self.db.commit()
        self.db.execute(text("set session_replication_role = replica"))
        self.db.execute(text(sql), params)
        self.db.commit()
        self.db.execute(text("set session_replication_role = origin"))
        self.db.commit()

    def _table_exists(self, name):
        return bool(self.db.scalar(text("select to_regclass(:n)"), {"n": name}))


class AtomicityTests(InventoryCase):
    def counts(self):
        self.db.expire_all()
        return tuple(self.db.scalar(text(f"select count(*) from {t}")) for t in ("stock_movements", "goods_receipts", "stock_adjustments", "part_purchases", "stock_reservations"))

    def test_a_failing_second_receipt_line_posts_nothing(self):
        a, b = self.make_item("ATM-A", "Atomic item A"), self.make_item("ATM-B", "Atomic item B")
        inv = self.purchase(self.make_supplier(), [(a["id"], 5, "10"), (b["id"], 5, "10")], receive=False)
        before = self.counts()
        l1, l2 = inv["lines"]
        with self.assertRaises(AppError):
            self.receive(inv, {l1["id"]: 5, l2["id"]: 6})  # line 2 exceeds what was ordered
        self.db.rollback()
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.bal(a["id"]).on_hand, D("0"))

    def test_a_failing_adjustment_line_changes_no_stock(self):
        a, b = self.make_item("ATM-C", "Atomic item C"), self.make_item("ATM-D", "Atomic item D")
        self.purchase(self.make_supplier(), [(a["id"], 5, "10"), (b["id"], 1, "10")])
        before = self.counts()
        body = api.AdjustmentIn(warehouse_id=self.wh.id, reason="atomicity test", lines=[api.AdjLine(item_id=a["id"], qty_delta=D("-2")), api.AdjLine(item_id=b["id"], qty_delta=D("-5"))])
        with self.assertRaises(AppError):
            api.create_adjustment(body, REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.bal(a["id"]).on_hand, D("5"))

    def test_adding_more_than_available_creates_no_job_part(self):
        item = self.make_item("ATM-E", "Atomic item E")
        self.purchase(self.make_supplier(), [(item["id"], 1, "10")])
        job = self.new_job()
        before = self.counts()
        with self.assertRaises(AppError):
            self.wpart(job, item["id"], 2)
        self.db.rollback()
        self.assertEqual(self.counts(), before)

    def test_issue_without_stock_leaves_the_part_status_and_stock_untouched(self):
        item = self.make_item("ATM-F", "Atomic item F")
        self.purchase(self.make_supplier(), [(item["id"], 2, "10")])
        job = self.new_job()
        part = self.wpart(job, item["id"], 2)
        self.db.execute(text("update inventory_balances set on_hand=0, value=0 where item_id=:i"), {"i": item["id"]})  # simulate a stock-take that emptied the shelf
        self.db.commit()
        with self.assertRaises(Exception):
            self.status(part["id"], "received")
        self.db.rollback()
        status = self.db.scalar(text("select status from part_purchases where id=:p"), {"p": part["id"]})
        self.assertNotEqual(status, "received")

    def test_duplicate_idempotency_key_returns_the_original_result_not_a_second_posting(self):
        item = self.make_item("ATM-G", "Atomic item G")
        inv = self.purchase(self.make_supplier(), [(item["id"], 4, "10")], receive=False)
        key = f"idem-{uuid.uuid4()}"
        r1 = self.receive(inv, {inv["lines"][0]["id"]: 4}, key=key)
        r2 = self.receive(inv, {inv["lines"][0]["id"]: 4}, key=key)
        self.assertEqual(self.bal(item["id"]).on_hand, D("4"))
        self.assertEqual(r1["id"], r2["id"])


if __name__ == "__main__":
    unittest.main()

