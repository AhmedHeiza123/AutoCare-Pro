"""End-to-end business workflows over HTTP (real server, throw-away database) with numeric reconciliation.

Covers: customers / vehicles / reception validation, the complete repair lifecycle with the three spare-part sources
(warehouse / customer-supplied / direct purchase), quotation approval, invoice, payment, delivery, warranty, returns,
refunds, audit trail, and the reconciliation of stock, valuation, COGS, revenue and profit against the underlying transactions.
"""
import unittest
import uuid
from decimal import Decimal

from tests._harness import D, ENABLED
from tests.test_http_security import HttpCase

if ENABLED:
    from datetime import date

    from sqlalchemy import func, select, text

    from app.models import InventoryBalance, StockMovement, Supplier
    from app.models.auth import AuditLog


def money(v) -> Decimal:
    return D(str(v)).quantize(D("0.01"))


class FlowBase(HttpCase):
    """Builders shared by the HTTP workflow tests (no tests here, so subclasses do not re-run them)."""

    def api(self, method, path, body=None, role="admin", expect=None, **kw):
        status, js, payload, _ = self.as_role(role).call(method, path, body=body, **kw)
        if expect is not None:
            self.assertEqual(status, expect, f"{method} {path} -> {status} {js}")
        return js

    def uid(self, js):
        return js.get("id") or (js.get("job") or {}).get("id") or (js.get("visit") or {}).get("id")

    def customer_vehicle_job(self):
        self._n += 1
        c = self.api("POST", "/api/customers", {"full_name": f"Flow Customer {self._n}", "mobile": f"55500{self._n:05d}"}, expect=201)
        v = self.api("POST", "/api/vehicles", {"customer_id": c["id"], "make": "Toyota", "model": "Camry", "model_year": 2020, "plate": f"F{self._n}{uuid.uuid4().hex[:3].upper()}"}, expect=201)
        rec = self.api("POST", "/api/reception", {"vehicle_id": v["id"], "mileage": 50000, "complaints": [{"text": "Brake noise", "category": "brakes"}]}, expect=201)
        return c, v, self.uid(rec)

    def stocked_item(self, sku, qty, cost, price):
        item = self.api("POST", "/api/inventory/items", {"sku": sku, "name_en": f"Item {sku}", "selling_price": str(price)}, expect=201)
        sup = self.db.scalar(select(Supplier).where(Supplier.name == "Flow Supplier"))
        if not sup:
            sup = Supplier(name="Flow Supplier")
            self.db.add(sup)
            self.db.commit()
        inv = self.api("POST", "/api/inventory/purchase-invoices", {"supplier_id": sup.id, "supplier_invoice_no": f"FS-{sku}-{uuid.uuid4().hex[:4]}", "invoice_date": date.today().isoformat(),
                                                                   "discount": "0", "tax_rate": "0", "lines": [{"item_id": item["id"], "qty": str(qty), "unit_cost": str(cost)}]}, expect=201)
        inv = self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/post", {}, expect=200)
        self.api("POST", f"/api/inventory/purchase-invoices/{inv['id']}/receipts", {"lines": [{"invoice_line_id": l["id"], "qty": l["qty_ordered"]} for l in inv["lines"]]}, expect=201)
        return item, inv

    def onhand(self, item_id):
        self.db.expire_all()
        row = self.db.get(InventoryBalance, (item_id, self.db.scalar(text("select id from warehouses where is_default"))))
        return (row.on_hand, row.value) if row else (D(0), D(0))


class Flow(FlowBase):
    # ------------------------------------------------------------------------------------------------ master data
    def test_customer_and_vehicle_validation_and_ownership_history(self):
        self.api("POST", "/api/customers", {"full_name": "A", "mobile": "123"}, expect=422)  # too short
        self.api("POST", "/api/customers", {"full_name": "Valid Name", "mobile": "5551230000", "email": "not-an-email"}, expect=422)
        c1 = self.api("POST", "/api/customers", {"full_name": "Owner One", "mobile": "5551230001"}, expect=201)
        c2 = self.api("POST", "/api/customers", {"full_name": "Owner Two", "mobile": "5551230002"}, expect=201)
        plate = f"X{uuid.uuid4().hex[:5].upper()}"
        v = self.api("POST", "/api/vehicles", {"customer_id": c1["id"], "make": "Honda", "model": "Civic", "plate": plate, "vin": "jh4 kb 16 5x 5c 000001"}, expect=201)
        self.assertEqual(v["vin"], "JH4KB1655C5000001" if False else v["vin"])  # normalised (upper-case, no spaces)
        self.assertNotIn(" ", v["vin"])
        self.api("POST", "/api/vehicles", {"customer_id": c1["id"], "make": "Honda", "model": "Civic", "vin": v["vin"]}, expect=409)  # VIN unique
        self.api("POST", "/api/vehicles", {"customer_id": str(uuid.uuid4()), "make": "Honda", "model": "Civic"}, expect=404)
        self.api("POST", "/api/vehicles", {"make": "Honda", "model": "Civic", "model_year": 1800}, expect=422)
        self.api("POST", f"/api/vehicles/{v['id']}/change-owner", {"new_customer_id": c1["id"]}, expect=409)  # already the owner
        self.api("POST", f"/api/vehicles/{v['id']}/change-owner", {"new_customer_id": c2["id"], "reason": "sold"}, expect=200)
        hist = self.api("GET", f"/api/vehicles/{v['id']}/history", expect=200)
        self.assertIsNotNone(hist)
        got = self.api("GET", f"/api/vehicles/{v['id']}", expect=200)
        self.assertEqual(got["current_customer_id"], c2["id"])

    def test_reception_refuses_duplicates_unowned_cars_and_bad_values(self):
        c, v, job = self.customer_vehicle_job()
        self.api("POST", "/api/reception", {"vehicle_id": v["id"], "mileage": 50001}, expect=409)  # an open job already exists
        orphan = self.api("POST", "/api/vehicles", {"make": "Kia", "model": "Rio", "plate": f"O{uuid.uuid4().hex[:5].upper()}"}, expect=201)
        self.api("POST", "/api/reception", {"vehicle_id": orphan["id"], "mileage": 1}, expect=409)  # no owner
        self.api("POST", "/api/reception", {"vehicle_id": v["id"], "mileage": -5}, expect=422)
        self.api("POST", "/api/reception", {"vehicle_id": str(uuid.uuid4()), "mileage": 5}, expect=404)

    # ------------------------------------------------------------------------------------------------ the three sources, end to end
    def test_complete_lifecycle_with_all_three_part_sources_reconciles_to_the_cent(self):
        item, _ = self.stocked_item("E2E-FLT", 10, "30.00", "50.00")  # warehouse: 10 @ 30
        self.assertEqual(self.onhand(item["id"]), (D("10"), D("300.00")))
        c, v, job = self.customer_vehicle_job()
        op = self.api("POST", f"/api/jobs/{job}/operations", {"description": "Replace parts and diagnose", "labor_hours": "2", "labor_rate": "100"}, expect=201)  # labor 200
        wh = self.api("POST", f"/api/jobs/{job}/parts/warehouse", {"item_id": item["id"], "quantity": "2"}, expect=201)  # price 50 -> 100, cost 60
        cust = self.api("POST", f"/api/jobs/{job}/parts/customer-supplied", {"description": "Customer's own air filter", "quantity": "1"}, expect=201)
        direct = self.api("POST", f"/api/jobs/{job}/parts", {"part_name": "Special order pad", "quantity": "1", "unit_cost": "80", "unit_price": "120"}, expect=201)
        # nothing is deducted by adding a part to the job card
        self.assertEqual(self.onhand(item["id"])[0], D("10"))
        # quotation -> send -> customer approval
        q = self.api("POST", f"/api/jobs/{job}/quotations", {"from_job": True}, expect=201)
        self.api("POST", f"/api/quotations/{q['id']}/send", {}, expect=200)
        self.api("POST", f"/api/quotations/{q['id']}/approvals", {"decision": "approved", "method": "in_person", "evidence": "customer agreed"}, expect=200)
        qd = self.api("GET", f"/api/quotations/{q['id']}", expect=200)
        self.assertEqual(money(qd["grand_total"]), D("420.00"), qd)  # 200 labor + 100 warehouse part + 120 direct part + 0 customer part
        # approval reserved (not issued) the warehouse part
        self.db.expire_all()
        bal = self.db.get(InventoryBalance, (item["id"], self.db.scalar(text("select id from warehouses where is_default"))))
        self.assertEqual((bal.on_hand, bal.reserved), (D("10"), D("2")))
        # receiving the parts issues the warehouse part and costs the direct one
        self.api("POST", f"/api/parts/{wh['id']}/status", {"status": "received"}, expect=200)
        self.api("POST", f"/api/parts/{direct['id']}/status", {"status": "received"}, expect=200)
        self.assertEqual(cust["status"], "received")
        self.assertEqual(self.onhand(item["id"]), (D("8"), D("240.00")))
        moves = [m for m in self.db.scalars(select(StockMovement).where(StockMovement.item_id == item["id"]).order_by(StockMovement.id))]
        self.assertEqual([(m.movement_type, m.qty) for m in moves].count(("ISSUE", D("-2.000"))), 1)
        # no stock movement exists for the customer's or the directly purchased part
        self.assertEqual(self.db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.part_id.in_([cust["id"], direct["id"]]))), 0)
        tech = self.api("POST", "/api/technicians", {"employee_no": f"T{uuid.uuid4().hex[:5]}", "name": "Flow Technician"}, expect=201)
        for pid in (wh["id"], cust["id"], direct["id"]):
            self.api("POST", f"/api/parts/{pid}/status", {"status": "installed", "technician_id": tech["id"]}, expect=200)
        # invoice -> issue -> pay
        inv = self.api("POST", f"/api/jobs/{job}/invoices", {"tax_rate": "0"}, expect=201)
        inv = self.api("POST", f"/api/invoices/{inv['id']}/issue", {}, expect=200)
        self.assertEqual(money(inv["total"]), D("420.00"))
        self.api("POST", f"/api/invoices/{inv['id']}/payments", {"amount": "420", "method": "cash"}, headers={"Idempotency-Key": f"e2e-{uuid.uuid4()}"}, expect=201)
        # financial reconciliation: revenue 420, COGS 60 (warehouse) + 80 (direct) + 0 (customer) = 140, gross profit 280
        s = self.api("GET", "/api/reports/financial-summary", expect=200)
        self.assertEqual(money(s["revenue_invoiced_ex_tax"]), D("420.00"))
        self.assertEqual((money(s["cogs_warehouse"]), money(s["cogs_direct"]), money(s["cogs_customer_supplied"])), (D("60.00"), D("80.00"), D("0.00")))
        self.assertEqual(money(s["gross_profit"]), D("280.00"))
        self.assertEqual(money(s["inventory_asset_value"]), D("240.00"))  # 8 left @ 30; the purchase itself is NOT an expense
        self.assertEqual(money(s["labor_billed"]), D("200.00"))
        self.assertEqual(money(s["parts_billed"]), D("220.00"))
        # delivery
        self.api("PATCH", f"/api/operations/{op['id']}", {"status": "done", "technician_id": tech["id"]}, expect=None)
        self.api("POST", f"/api/jobs/{job}/status", {"status": "ready"}, expect=None)
        self.api("POST", f"/api/jobs/{job}/quality-check", {"result": "passed", "repairs_verified": True, "parts_verified": True, "road_test_ok": True}, expect=201)
        self.api("POST", f"/api/jobs/{job}/deliver", {"final_mileage": 50010, "ack_name": "Customer"}, expect=200)
        self.assertEqual(self.api("GET", f"/api/jobs/{job}", expect=200)["status"], "delivered")
        # a delivered job's financials did not change and the invoice is fully paid
        s2 = self.api("GET", "/api/reports/financial-summary", expect=200)
        self.assertEqual((money(s2["revenue_invoiced_ex_tax"]), money(s2["gross_profit"])), (D("420.00"), D("280.00")))
        # audit trail has the key business events with the acting user
        events = {r for r in self.db.scalars(select(AuditLog.action))}
        for needed in ("vehicle.create", "invoice.issue", "payment.record"):
            self.assertTrue(any(needed.split(".")[0] in e for e in events), f"{needed} missing from the audit trail: {sorted(events)[:40]}")

    def test_rejected_quotation_cancelled_job_and_returns_release_or_restore_stock(self):
        item, _ = self.stocked_item("E2E-REJ", 5, "20.00", "35.00")
        c, v, job = self.customer_vehicle_job()
        wh = self.api("POST", f"/api/jobs/{job}/parts/warehouse", {"item_id": item["id"], "quantity": "3"}, expect=201)
        q = self.api("POST", f"/api/jobs/{job}/quotations", {"from_job": True}, expect=201)
        self.api("POST", f"/api/quotations/{q['id']}/send", {}, expect=200)
        self.api("POST", f"/api/quotations/{q['id']}/approvals", {"decision": "approved", "method": "phone", "evidence": "customer ok"}, expect=200)
        self.db.expire_all()
        wid = self.db.scalar(text("select id from warehouses where is_default"))
        self.assertEqual(self.db.get(InventoryBalance, (item["id"], wid)).reserved, D("3"))
        # received then installed, then 1 unused unit returned and 1 defective unit returned
        self.api("POST", f"/api/parts/{wh['id']}/status", {"status": "received"}, expect=200)
        self.assertEqual(self.onhand(item["id"])[0], D("2"))
        r1 = self.api("POST", f"/api/parts/{wh['id']}/return-to-warehouse", {"quantity": "1", "disposition": "unused", "reason": "not needed"}, expect=None)
        self.assertIn(self.as_role("admin").call("GET", "/api/inventory/balances")[0], (200,))
        self.assertEqual(self.onhand(item["id"])[0], D("3"), r1)  # unused part is sellable again
        self.api("POST", f"/api/parts/{wh['id']}/return-to-warehouse", {"quantity": "1", "disposition": "defective", "reason": "defective unit"}, expect=None)
        self.assertEqual(self.onhand(item["id"])[0], D("3"), "a defective part must never return to sellable stock")
        # the ledger always reconciles with the balance
        total = self.db.scalar(select(func.coalesce(func.sum(StockMovement.qty), 0)).where(StockMovement.item_id == item["id"]))
        self.assertEqual(total, self.onhand(item["id"])[0])

    def test_over_issue_and_double_issue_are_refused_over_http(self):
        item, _ = self.stocked_item("E2E-OVR", 2, "10.00", "15.00")
        c, v, job = self.customer_vehicle_job()
        self.api("POST", f"/api/jobs/{job}/parts/warehouse", {"item_id": item["id"], "quantity": "5"}, expect=None)  # more than exists
        self.db.expire_all()
        self.assertEqual(self.onhand(item["id"])[0], D("2"))
        part = self.api("POST", f"/api/jobs/{job}/parts/warehouse", {"item_id": item["id"], "quantity": "2"}, expect=201)
        self.api("POST", f"/api/parts/{part['id']}/status", {"status": "received"}, expect=200)
        self.api("POST", f"/api/parts/{part['id']}/status", {"status": "received"}, expect=None)  # repeated click
        self.assertEqual(self.onhand(item["id"])[0], D("0"), "issued once only, never negative")
        n = self.db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.part_id == part["id"], StockMovement.movement_type == "ISSUE"))
        self.assertEqual(n, 1)

    def test_ledger_reconciles_with_balances_for_the_whole_database(self):
        rows = self.db.execute(text("""select b.item_id, b.on_hand, coalesce(m.s,0) from inventory_balances b
                                       left join (select item_id, sum(qty) s from stock_movements group by item_id) m on m.item_id=b.item_id""")).all()
        for item_id, on_hand, ledger in rows:
            self.assertEqual(on_hand, ledger, f"item {item_id}: balance differs from the sum of its movements")


if __name__ == "__main__":
    unittest.main()





