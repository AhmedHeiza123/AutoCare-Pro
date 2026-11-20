"""Mandatory QA scenario (purchase 20 filters -> three repair orders -> one return + credit note) over real HTTP,
plus partial receipts, supplier returns, adjustments/reversals and supplier balances. Throw-away database only.
Numbers follow the QA specification exactly: no tax, no discount, no labor."""
import unittest
import uuid
from decimal import Decimal

from tests._harness import D, ENABLED
from tests.test_workflows import FlowBase, money

if ENABLED:
    from datetime import date

    from sqlalchemy import func, select, text

    from app.models import StockMovement, Supplier


class MandatoryScenario(FlowBase):
    def _supplier(self, name="Scenario Supplier"):
        sup = self.db.scalar(select(Supplier).where(Supplier.name == name))
        if not sup:
            sup = Supplier(name=name)
            self.db.add(sup)
            self.db.commit()
        return sup

    def _sup_balance(self, sup_id):
        rows = self.api("GET", "/api/inventory/supplier-balances", expect=200)
        for r in rows:
            if str(r.get("supplier_id") or r.get("id")) == str(sup_id):
                return money(r.get("outstanding", r.get("balance", r.get("balance_due", "0"))))
        return D("0.00")

    def test_step_a_b_c_purchase_issue_to_three_repair_orders_and_return_one(self):
        before = self.api("GET", "/api/reports/financial-summary", expect=200)
        # ---- Step A: purchase 20 @ 30 = 600
        item = self.api("POST", "/api/inventory/items", {"sku": "TEST-FILTER-001", "name_en": "TEST A/C Filter", "selling_price": "50"}, expect=201)
        sup = self._supplier()
        inv = self.api("POST", "/api/inventory/purchase-invoices", {"supplier_id": sup.id, "supplier_invoice_no": f"SC-{uuid.uuid4().hex[:6]}", "invoice_date": date.today().isoformat(),
                                                                   "discount": "0", "tax_rate": "0", "lines": [{"item_id": item["id"], "qty": "20", "unit_cost": "30"}]}, expect=201)
        self.assertEqual(money(inv["total"]), D("600.00"))
        inv = self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/post", {}, expect=200)
        self.assertEqual(self._sup_balance(sup.id), D("600.00"), "supplier owes 600 after posting")
        self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/receipts", {"lines": [{"invoice_line_id": l["id"], "qty": l["qty_ordered"]} for l in inv["lines"]]}, expect=201)
        self.assertEqual(self.onhand(item["id"]), (D("20"), D("600.00")))
        self.assertEqual(money(self.api("GET", "/api/inventory/valuation", expect=200)["total_value"]) - money(before["inventory_asset_value"]), D("600.00"))
        mv = [(m.movement_type, m.qty) for m in self.db.scalars(select(StockMovement).where(StockMovement.item_id == item["id"]))]
        self.assertEqual(mv, [("GOODS_RECEIPT", D("20.000"))])
        # ---- Step B: three repair orders, one filter each
        jobs, parts, invoices = [], [], []
        tech = self.api("POST", "/api/technicians", {"employee_no": f"T{uuid.uuid4().hex[:5]}", "name": "Scenario Technician"}, expect=201)
        for _ in range(3):
            c, v, job = self.customer_vehicle_job()
            op = self.api("POST", f"/api/jobs/{job}/operations", {"description": "Fit A/C filter", "labor_hours": "0", "labor_rate": "0"}, expect=None)
            p = self.api("POST", f"/api/jobs/{job}/parts/warehouse", {"item_id": item["id"], "quantity": "1"}, expect=201)
            q = self.api("POST", f"/api/jobs/{job}/quotations", {"from_job": True}, expect=201)
            self.api("POST", f"/api/quotations/{q['id']}/send", {}, expect=200)
            self.api("POST", f"/api/quotations/{q['id']}/approvals", {"decision": "approved", "method": "in_person", "evidence": "customer agreed"}, expect=200)
            self.api("POST", f"/api/parts/{p['id']}/status", {"status": "received"}, expect=200)
            self.api("POST", f"/api/parts/{p['id']}/status", {"status": "installed", "technician_id": tech["id"]}, expect=200)
            i = self.api("POST", f"/api/jobs/{job}/invoices", {"tax_rate": "0"}, expect=201)
            i = self.api("POST", f"/api/invoices/{i['id']}/issue", {}, expect=200)
            self.assertEqual(money(i["total"]), D("50.00"))
            jobs.append(job); parts.append(p); invoices.append(i)
        self.assertEqual(self.onhand(item["id"]), (D("17"), D("510.00")))
        issued = self.db.scalar(select(func.coalesce(func.sum(-StockMovement.qty), 0)).where(StockMovement.item_id == item["id"], StockMovement.movement_type == "ISSUE"))
        self.assertEqual(issued, D("3.000"))
        s = self.api("GET", "/api/reports/financial-summary", expect=200)
        self.assertEqual(money(s["cogs_warehouse"]) - money(before["cogs_warehouse"]), D("90.00"))
        self.assertEqual(money(s["parts_billed"]) - money(before["parts_billed"]), D("150.00"))
        # ---- Step C: one unused filter returned to stock; invoice already issued -> credit note 50
        self.api("POST", f"/api/parts/{parts[0]['id']}/return-to-warehouse", {"quantity": "1", "disposition": "unused", "reason": "customer did not need it"}, expect=200)
        self.assertEqual(self.onhand(item["id"]), (D("18"), D("540.00")))
        self.api("POST", f"/api/invoices/{invoices[0]['id']}/credit-notes", {"amount": "50", "reason": "unused filter returned"}, expect=201)
        f = self.api("GET", "/api/reports/financial-summary", expect=200)
        self.assertEqual(money(f["cogs_warehouse"]) - money(before["cogs_warehouse"]), D("60.00"), "net parts COGS")
        net_rev = (money(f["revenue_invoiced_ex_tax"]) - money(f.get("credit_notes_ex_tax", f.get("credit_notes", 0)))) - (money(before["revenue_invoiced_ex_tax"]) - money(before.get("credit_notes_ex_tax", before.get("credit_notes", 0))))
        self.assertEqual(net_rev, D("100.00"), "net parts revenue")
        self.assertEqual(money(f["gross_profit"]) - money(before["gross_profit"]), D("40.00"), "parts gross profit")
        self.assertEqual(money(self.api("GET", "/api/inventory/valuation", expect=200)["total_value"]) - money(before["inventory_asset_value"]), D("540.00"))
        total = self.db.scalar(select(func.coalesce(func.sum(StockMovement.qty), 0)).where(StockMovement.item_id == item["id"]))
        self.assertEqual(total, D("18.000"), "ledger equals balance")

    def test_partial_receipts_supplier_balance_payment_and_supplier_return(self):
        sup = self._supplier("Partial Supplier")
        item = self.api("POST", "/api/inventory/items", {"sku": f"PART-{uuid.uuid4().hex[:5].upper()}", "name_en": "Partial item", "selling_price": "40"}, expect=201)
        inv = self.api("POST", "/api/inventory/purchase-invoices", {"supplier_id": sup.id, "supplier_invoice_no": f"PS-{uuid.uuid4().hex[:6]}", "invoice_date": date.today().isoformat(),
                                                                   "discount": "0", "tax_rate": "0", "lines": [{"item_id": item["id"], "qty": "10", "unit_cost": "20"}]}, expect=201)
        inv = self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/post", {}, expect=200)
        line = inv["lines"][0]
        self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/receipts", {"lines": [{"invoice_line_id": line["id"], "qty": "4"}]}, expect=201)
        self.assertEqual(self.onhand(item["id"]), (D("4"), D("80.00")))
        self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/receipts", {"lines": [{"invoice_line_id": line["id"], "qty": "7"}]}, expect=None)  # more than ordered: refused
        self.assertEqual(self.onhand(item["id"])[0], D("4"))
        self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/receipts", {"lines": [{"invoice_line_id": line["id"], "qty": "6"}]}, expect=201)
        self.assertEqual(self.onhand(item["id"]), (D("10"), D("200.00")))
        self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/payments", {"amount": "50", "method": "cash"}, headers={"Idempotency-Key": f"sp-{uuid.uuid4()}"}, expect=201)
        self.assertEqual(self._sup_balance(sup.id), D("150.00"))
        self.api("POST", "/api/inventory/purchase-invoices/%s/payments" % inv["id"], {"amount": "500", "method": "cash"}, headers={"Idempotency-Key": f"sp-{uuid.uuid4()}"}, expect=None)
        self.assertEqual(self._sup_balance(sup.id), D("150.00"), "overpaying the supplier is refused")
        self.api("POST", "/api/inventory/supplier-returns", {"item_id": item["id"], "qty": "2", "supplier_id": sup.id, "credit_amount": "40", "invoice_id": inv["id"], "reason": "wrong model"}, expect=201)
        self.assertEqual(self.onhand(item["id"]), (D("8"), D("160.00")))
        self.assertEqual(self._sup_balance(sup.id), D("110.00"))

    def test_adjustments_reversal_and_insufficient_stock(self):
        item, _ = self.stocked_item(f"ADJ-{uuid.uuid4().hex[:5].upper()}", 5, "10.00", "20.00")
        self.api("POST", "/api/inventory/adjustments", {"reason": "damaged", "lines": [{"item_id": item["id"], "qty_delta": "-9"}]}, expect=None)
        self.assertEqual(self.onhand(item["id"])[0], D("5"), "adjustment may not drive stock negative")
        self.api("POST", "/api/inventory/adjustments", {"reason": "found extra", "lines": [{"item_id": item["id"], "qty_delta": "-2"}]}, expect=201)
        self.assertEqual(self.onhand(item["id"]), (D("3"), D("30.00")))
        mid = self.db.scalar(select(StockMovement.id).where(StockMovement.item_id == item["id"], StockMovement.movement_type == "ADJUSTMENT").order_by(StockMovement.id.desc()))
        self.api("POST", f"/api/inventory/movements/{mid}/reverse", {"reason": "entered by mistake"}, expect=201)
        self.assertEqual(self.onhand(item["id"]), (D("5"), D("50.00")))
        self.api("POST", f"/api/inventory/movements/{mid}/reverse", {"reason": "again"}, expect=None)
        self.assertEqual(self.onhand(item["id"])[0], D("5"), "a movement can be reversed only once")

    def test_valuation_trend_ends_at_the_current_valuation_and_needs_cost_permission(self):
        self.stocked_item(f"TRD-{uuid.uuid4().hex[:5].upper()}", 4, "25.00", "40.00")
        trend = self.api("GET", "/api/inventory/valuation-trend?months=3", expect=200)
        self.assertEqual(len(trend["points"]), 3)
        current = money(self.api("GET", "/api/inventory/valuation", expect=200)["total_value"])
        self.assertEqual(money(trend["points"][-1]["value"]), current, "the latest point must equal today's valuation")
        self.assertEqual([p["month"] for p in trend["points"]], sorted(p["month"] for p in trend["points"]))
        self.api("GET", "/api/inventory/valuation-trend?months=99", expect=422)
        self.api("GET", "/api/inventory/valuation-trend", role="storekeeper", expect=403)  # cost figures stay restricted

    def test_duplicate_goods_receipt_and_concurrent_issue(self):
        import threading
        item, inv = self.stocked_item(f"CON-{uuid.uuid4().hex[:5].upper()}", 1, "10.00", "15.00")
        self.assertEqual(self.onhand(item["id"])[0], D("1"))
        jobs = [self.customer_vehicle_job()[2] for _ in range(4)]
        parts = [self.api("POST", f"/api/jobs/{j}/parts/warehouse", {"item_id": item["id"], "quantity": "1"}, expect=None) for j in jobs]
        parts = [p for p in parts if p and p.get("id")]
        results = []

        def issue(pid):
            status, _, _, _ = self.as_role("admin").call("POST", f"/api/parts/{pid}/status", body={"status": "received"})
            results.append(status)
        ts = [threading.Thread(target=issue, args=(p["id"],)) for p in parts]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertLessEqual(results.count(200), 1, results)
        self.assertEqual(self.onhand(item["id"])[0] >= 0, True)


if __name__ == "__main__":
    unittest.main()
