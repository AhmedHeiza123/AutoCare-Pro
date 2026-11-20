"""Regression tests for the financial audit (invoices, discounts, COGS, returns, credit notes, reports).

Each test states the expected, accounting-correct behaviour. Tests in AuditedBugs failed before the fixes (see the audit report);
the other classes pin behaviour that was verified as correct so it cannot regress.
"""
import unittest
import uuid
from datetime import date

from tests._harness import D, ENABLED, FinanceCase, REQ

if ENABLED:
    from fastapi import HTTPException  # noqa: F401
    from sqlalchemy import select

    from app.api import billing, parts, quotes
    from app.core.errors import AppError
    from app.models import ExpenseCategory, Invoice


def money(x):
    return D(str(x)).quantize(D("0.01"))


# =====================================================================================================================
class InvoiceArithmetic(FinanceCase):
    """Verified-correct behaviour: totals, tax, discount, payments, refunds, credit notes, outstanding balance."""

    def test_totals_discount_then_tax(self):
        job = self.new_job()
        self.add_labor(job, 600)
        self.add_part(job, 1, 250, 400)
        inv = self.invoice(job, discount=100, tax_rate="5")
        # (600 + 400 - 100) * 1.05
        self.assertEqual((inv["subtotal"], inv["tax_amount"], inv["total"]), ("1000.00", "45.00", "945.00"))
        self.assertEqual(inv["outstanding"], "945.00")
        self.assertEqual(inv["payment_status"], "unpaid")

    def test_partial_payment_overpayment_and_refund(self):
        job = self.new_job()
        self.add_labor(job, 1000)
        inv = self.invoice(job)
        self.pay(inv["id"], 400)
        state = billing.invoice_out(self.db, self.db.get(Invoice, inv["id"]))
        self.assertEqual((state["paid"], state["outstanding"], state["payment_status"]), ("400.00", "600.00", "partial"))
        with self.assertRaises(AppError):  # more than the balance
            self.pay(inv["id"], 700)
        self.db.rollback()
        payment_id = state["payments"][0]["id"]
        billing.refund_payment(payment_id, billing.RefundIn(amount=D("150"), reason="partial refund"), REQ, user=self.user, db=self.db)
        self.db.commit()
        state = billing.invoice_out(self.db, self.db.get(Invoice, inv["id"]))
        self.assertEqual((state["net_paid"], state["outstanding"]), ("250.00", "750.00"))
        with self.assertRaises(AppError):  # cannot refund more than was paid
            billing.refund_payment(payment_id, billing.RefundIn(amount=D("300"), reason="too much"), REQ, user=self.user, db=self.db)
        self.db.rollback()

    def test_credit_note_reduces_balance_and_cannot_exceed_total(self):
        job = self.new_job()
        self.add_labor(job, 1000)
        inv = self.invoice(job)
        out = self.credit(inv["id"], 250)
        self.assertEqual((out["credit_total"], out["due"], out["outstanding"]), ("250.00", "750.00", "750.00"))
        with self.assertRaises(AppError):
            self.credit(inv["id"], 800)
        self.db.rollback()

    def test_sql_payment_status_filter_agrees_with_python_state(self):
        scenarios = []
        for amount, paid, credit in [(1000, 0, 0), (1000, 400, 0), (1000, 1000, 0), (1000, 600, 400), (1000, 0, 1000)]:
            job = self.new_job()
            self.add_labor(job, amount)
            inv = self.invoice(job)
            if credit:
                self.credit(inv["id"], credit)
            if paid:
                self.pay(inv["id"], paid)
            scenarios.append(inv["id"])
        for status in ("unpaid", "partial", "paid", "overpaid"):
            listed = {r["id"] for r in billing.list_invoices(status="issued", payment_status=status, customer_id=None, limit=200, offset=0,
                                                              _=self.user, db=self.db)}
            expected = {i for i in scenarios if billing.invoice_out(self.db, self.db.get(Invoice, i))["payment_status"] == status}
            self.assertEqual(listed, expected, status)


# =====================================================================================================================
class AuditedBugs(FinanceCase):

    # ---- 1. quotation discount must reach the invoice ---------------------------------------------------------------
    def _approved_quote(self, job, discount, tax, approve_all=True):
        quote = quotes.create_quote(job.id, quotes.QuoteCreate(from_job=True, discount=D(str(discount)), tax_rate=D(str(tax))),
                                    REQ, user=self.user, db=self.db)
        self.db.commit()
        quotes.send_quote(quote["id"], REQ, user=self.user, db=self.db)
        self.db.commit()
        if approve_all:
            quotes.record_approval(quote["id"], quotes.ApprovalIn(decision="approved", method="in_person", evidence="customer agreed"),
                                   REQ, user=self.user, db=self.db)
            self.db.commit()
        return quote

    def test_invoice_from_quotation_carries_the_quote_discount(self):
        job = self.new_job()
        self.add_labor(job, 600)
        self.add_part(job, 1, 250, 400)
        quote = self._approved_quote(job, discount=100, tax=5)
        self.assertEqual(quote["grand_total"], "945.00")  # what the customer agreed to pay
        body = billing.InvoiceCreate(quotation_id=uuid.UUID(quote["id"]))
        inv = billing.create_invoice(job.id, body, REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(inv["discount"], "100.00")
        self.assertEqual(inv["total"], "945.00")

    def test_partial_approval_prorates_the_quote_discount(self):
        job = self.new_job()
        self.add_labor(job, 600, "Labor A")
        self.add_part(job, 1, 250, 400, "Part B")
        quote = self._approved_quote(job, discount=100, tax=0, approve_all=False)
        items = {i["description"]: i["id"] for i in quote["items"]}
        quotes.record_approval(quote["id"], quotes.ApprovalIn(
            decisions=[quotes.Decision(item_id=items["Labor A"], decision="approved"), quotes.Decision(item_id=items["Part B"], decision="rejected")],
            method="in_person", evidence="labor only"), REQ, user=self.user, db=self.db)
        self.db.commit()
        approved = quotes.get_quote(quote["id"], _=self.user, db=self.db)
        self.assertEqual(approved["approved_amount"], "540.00")  # 600 of 1000 approved -> 600 - 60 discount
        body = billing.InvoiceCreate(quotation_id=uuid.UUID(quote["id"]))
        inv = billing.create_invoice(job.id, body, REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual((inv["subtotal"], inv["discount"], inv["total"]), ("600.00", "60.00", "540.00"))

    # ---- 2. discount must be reflected in the revenue categories -----------------------------------------------------
    def test_revenue_categories_reconcile_with_discounted_revenue(self):
        job = self.new_job()
        self.add_labor(job, 600)
        self.add_part(job, 1, 250, 400)
        self.invoice(job, discount=100, tax_rate="0")
        s = self.summary()
        self.assertEqual(s["revenue_invoiced_ex_tax"], D("900.00"))
        self.assertEqual(s["labor_net"] + s["parts_net"] + s["other_net"], s["revenue_invoiced_ex_tax"])
        self.assertEqual((s["labor_net"], s["parts_net"]), (D("540.00"), D("360.00")))
        self.assertEqual(s["discount_invoiced"], D("100.00"))
        # the gross (pre-discount) figures stay available and unchanged for existing consumers
        self.assertEqual((s["labor_billed"], s["parts_billed"]), (D("600.00"), D("400.00")))

    def test_category_allocation_never_loses_a_cent(self):
        job = self.new_job()
        self.add_labor(job, "100.01", "Labor odd")
        self.add_part(job, 1, 10, "100.01", "Part one")
        self.add_part(job, 1, 10, "100.01", "Part two")
        self.invoice(job, discount="0.99", tax_rate="0")
        s = self.summary()
        self.assertEqual(s["labor_net"] + s["parts_net"] + s["other_net"], s["revenue_invoiced_ex_tax"])

    # ---- 3. COGS must follow returns and credit notes ---------------------------------------------------------------
    def test_cogs_reduced_when_a_billed_part_is_returned_after_invoicing(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        inv = self.invoice(job)  # revenue 200, COGS 100
        s0 = self.summary()
        self.assertEqual((s0["net_revenue_ex_tax"], s0["direct_costs_parts"], s0["gross_profit"]), (D("200.00"), D("100.00"), D("100.00")))
        self.return_part(part["id"], 1, refund=50)  # one unit goes back to the supplier ...
        self.credit(inv["id"], 100)  # ... and the customer is credited for it
        s1 = self.summary()
        self.assertEqual(s1["net_revenue_ex_tax"], D("100.00"))
        self.assertEqual(s1["direct_costs_parts"], D("50.00"))  # only the unit the customer kept
        self.assertEqual(s1["gross_profit"], D("50.00"))

    def test_return_before_invoicing_does_not_touch_cogs(self):
        job = self.new_job()
        part = self.add_part(job, 3, 50, 100)
        self.return_part(part["id"], 1)  # 1 of 3 returned before anything was billed
        self.invoice(job)  # bills the 2 kept units
        s = self.summary()
        self.assertEqual((s["net_revenue_ex_tax"], s["direct_costs_parts"], s["gross_profit"]), (D("200.00"), D("100.00"), D("100.00")))

    def test_return_of_unbilled_units_after_invoicing_does_not_touch_cogs(self):
        job = self.new_job()
        part = self.add_part(job, 3, 50, 100)
        self.invoice(job, scope="parts")  # bills all 3
        # a supplemental part that was never billed
        part2 = self.add_part(job, 2, 40, 80, "Unbilled part")
        self.return_part(part2["id"], 2)
        s = self.summary()
        self.assertEqual(s["direct_costs_parts"], D("150.00"))

    def test_job_profit_report_nets_credit_notes_and_returned_parts(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        inv = self.invoice(job)
        self.return_part(part["id"], 1)
        self.credit(inv["id"], 100)
        rows = self.report("job-profit")["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["revenue"], rows[0]["cost"], rows[0]["profit"]), ("100.00", "50.00", "50.00"))

    def test_gross_profit_equals_sum_of_job_profit_report(self):
        for qty, cost, price, discount, ret, credit in [(2, 50, 100, 0, 1, 100), (3, 20, 70, 30, 0, 0), (1, 10, 25, 5, 0, 10)]:
            job = self.new_job()
            self.add_labor(job, 100)
            part = self.add_part(job, qty, cost, price)
            inv = self.invoice(job, discount=discount)
            if ret:
                self.return_part(part["id"], ret)
            if credit:
                self.credit(inv["id"], credit)
        summary = self.summary()
        report = self.report("job-profit")
        self.assertEqual(sum(D(r["profit"]) for r in report["rows"]), summary["gross_profit"])
        self.assertEqual(sum(D(r["revenue"]) for r in report["rows"]), summary["net_revenue_ex_tax"])
        self.assertEqual(sum(D(r["cost"]) for r in report["rows"]), summary["direct_costs_parts"])

    # ---- 4. historical costs/prices must not change after invoicing ------------------------------------------------
    def test_part_cost_and_price_are_locked_once_billed(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        self.invoice(job)
        for change in ({"unit_cost": D("80")}, {"unit_price": D("120")}):
            with self.assertRaises(AppError) as ctx:
                parts.update_part(part["id"], parts.PartPatch(**change), REQ, user=self.user, db=self.db)
            self.db.rollback()
            self.assertEqual(ctx.exception.code, "part_invoiced")
        # editing a note stays possible, and COGS did not move
        parts.update_part(part["id"], parts.PartPatch(notes="checked"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(self.summary()["direct_costs_parts"], D("100.00"))

    def test_unbilled_part_can_still_be_repriced(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        out = parts.update_part(part["id"], parts.PartPatch(unit_cost=D("55"), unit_price=D("110")), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual((D(out["unit_cost"]), D(out["unit_price"])), (D("55"), D("110")))

    # ---- 5. tax reporting after credit notes ------------------------------------------------------------------------
    def test_tax_on_credit_notes_is_reported(self):
        job = self.new_job()
        self.add_labor(job, 1000)
        inv = self.invoice(job, tax_rate="5")  # total 1050, tax 50
        self.credit(inv["id"], "105.00")  # credit incl. 5 tax
        s = self.summary()
        self.assertEqual((s["tax_invoiced"], s["tax_credited"], s["net_tax"]), (D("50.00"), D("5.00"), D("45.00")))
        self.assertEqual(s["net_revenue_ex_tax"], D("900.00"))


# =====================================================================================================================
class ReportConsistency(FinanceCase):
    """Verified-correct: receivables, cash and the different report views agree with the underlying transactions."""

    def test_receivables_cash_and_revenue_match_transactions(self):
        a, b = self.new_job(), self.new_job()
        self.add_labor(a, 1000)
        self.add_labor(b, 500)
        ia = self.invoice(a, tax_rate="5")  # 1050
        ib = self.invoice(b, tax_rate="0")  # 500
        self.pay(ia["id"], 300)
        self.pay(ib["id"], 500)
        self.credit(ia["id"], 50)
        s = self.summary()
        self.assertEqual(s["receivables_outstanding"], D("700.00"))  # 1050 - 50 - 300
        self.assertEqual(s["cash_received"], D("800.00"))
        self.assertEqual(s["revenue_invoiced_ex_tax"], D("1500.00"))
        self.assertEqual(s["invoices_issued"], 2)
        outstanding_report = self.report("outstanding")
        self.assertEqual(sum(D(r["outstanding"]) for r in outstanding_report["rows"]), s["receivables_outstanding"])

    def test_cancelled_and_draft_invoices_never_count(self):
        job = self.new_job()
        self.add_labor(job, 400)
        draft = self.invoice(job, issue=False)
        self.assertEqual(self.summary()["invoices_issued"], 0)
        billing.issue_invoice(draft["id"], REQ, user=self.user, db=self.db)
        self.db.commit()
        billing.cancel_invoice(draft["id"], billing.ReasonIn(reason="entered by mistake"), REQ, user=self.user, db=self.db)
        self.db.commit()
        s = self.summary()
        self.assertEqual((s["invoices_issued"], s["net_revenue_ex_tax"], s["receivables_outstanding"]), (0, D("0.00"), D("0.00")))

    def test_deposit_is_applied_to_the_invoice_and_counted_once_in_cash(self):
        job = self.new_job()
        self.add_labor(job, 1000)
        billing.record_deposit(job.id, billing.PaymentIn(amount=D("300"), method="cash"), REQ, idempotency_key=None, user=self.user, db=self.db)
        self.db.commit()
        inv = self.invoice(job)
        self.assertEqual((inv["paid"], inv["outstanding"]), ("300.00", "700.00"))
        s = self.summary()
        self.assertEqual((s["cash_received"], s["receivables_outstanding"]), (D("300.00"), D("700.00")))

    def test_expenses_reduce_net_profit_and_voided_ones_do_not(self):
        from app.api import finance
        job = self.new_job()
        self.add_labor(job, 1000)
        self.invoice(job)
        cat = self.db.scalar(select(ExpenseCategory))
        e1 = finance.create_expense(finance.ExpenseIn(category_id=cat.id, amount=D("200"), expense_date=date.today(), description="rent"),
                                    REQ, user=self.user, db=self.db)
        e2 = finance.create_expense(finance.ExpenseIn(category_id=cat.id, amount=D("50"), expense_date=date.today(), description="oops"),
                                    REQ, user=self.user, db=self.db)
        self.db.commit()
        finance.void_expense(e2["id"], finance.VoidIn(reason="duplicate entry"), REQ, user=self.user, db=self.db)
        self.db.commit()
        s = self.summary()
        self.assertEqual((s["operating_expenses"], s["gross_profit"], s["estimated_net_profit"]), (D("200.00"), D("1000.00"), D("800.00")))


# =====================================================================================================================
class ProbedBehaviour(FinanceCase):
    """Edge cases probed during the audit (credit reversals, cancelled parts, supplemental invoices, rounding)."""

    def test_cancelling_a_credit_note_restores_balance_and_report_figures(self):
        job = self.new_job()
        self.add_labor(job, 1000)
        inv = self.invoice(job)
        self.credit(inv["id"], 200)
        credit_id = billing.invoice_out(self.db, self.db.get(Invoice, inv["id"]))["credit_notes"][0]["id"]
        billing.cancel_credit_note(credit_id, billing.ReasonIn(reason="issued by mistake"), REQ, user=self.user, db=self.db)
        self.db.commit()
        state = billing.invoice_out(self.db, self.db.get(Invoice, inv["id"]))
        self.assertEqual((state["credit_total"], state["outstanding"]), ("0.00", "1000.00"))
        s = self.summary()
        self.assertEqual((s["credit_notes"], s["net_revenue_ex_tax"]), (D("0.00"), D("1000.00")))

    def test_a_billed_part_cannot_be_cancelled(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        self.invoice(job)
        with self.assertRaises(AppError) as ctx:
            parts.part_status(part["id"], parts.PartStatusIn(status="cancelled"), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "part_invoiced")

    def test_an_unbilled_part_can_still_be_cancelled(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        out = parts.part_status(part["id"], parts.PartStatusIn(status="cancelled"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(out["status"], "cancelled")

    def test_supplemental_invoice_never_bills_the_same_part_twice(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        self.invoice(job)
        parts.update_part(part["id"], parts.PartPatch(quantity=D("3")), REQ, user=self.user, db=self.db)  # one more unit used
        self.db.commit()
        second = self.invoice(job, supplemental=True)
        self.assertEqual(second["subtotal"], "100.00")  # only the extra unit
        s = self.summary()
        self.assertEqual((s["net_revenue_ex_tax"], s["direct_costs_parts"]), (D("300.00"), D("150.00")))

    def test_rounding_with_many_fractional_lines_stays_consistent(self):
        job = self.new_job()
        for i in range(7):
            self.add_part(job, "1.33", "7.77", "12.34", f"Part number {i}")
        self.add_labor(job, "33.33", "Labor fractions")
        inv = self.invoice(job, discount="3.33", tax_rate="5")
        subtotal = sum(D(i["amount"]) for i in inv["items"])
        self.assertEqual(D(inv["subtotal"]), subtotal)
        net = subtotal - D("3.33")
        self.assertEqual(D(inv["tax_amount"]), (net * D("0.05")).quantize(D("0.01"), rounding="ROUND_HALF_UP"))
        self.assertEqual(D(inv["total"]), net + D(inv["tax_amount"]))
        self.assertEqual(D(inv["outstanding"]), D(inv["total"]))


class AllocationRules(unittest.TestCase):
    """Pure rules (no database)."""

    @classmethod
    def setUpClass(cls):
        if not ENABLED:
            raise unittest.SkipTest("set AUTOCARE_TEST_DATABASE_URL to a database whose name contains 'test'")

    def test_allocate_discount_is_proportional_and_exact(self):
        from app.services.accounting import allocate_discount
        net = allocate_discount({"labor": D("600.00"), "part": D("400.00"), "other": D("0.00")}, D("100.00"))
        self.assertEqual(net, {"labor": D("540.00"), "part": D("360.00"), "other": D("0.00")})

    def test_allocate_discount_rounding_goes_to_the_largest_category_and_sums_exactly(self):
        from app.services.accounting import allocate_discount
        for discount in ("0.01", "0.99", "3.33", "33.33", "100.00"):
            amounts = {"labor": D("100.01"), "part": D("200.02"), "other": D("33.33")}
            net = allocate_discount(amounts, D(discount))
            self.assertEqual(sum(net.values()), sum(amounts.values()) - D(discount))
            self.assertTrue(all(v >= 0 for v in net.values()))

    def test_allocate_discount_without_discount_is_identity(self):
        from app.services.accounting import allocate_discount
        amounts = {"labor": D("10.00"), "part": D("5.00"), "other": D("0.00")}
        self.assertEqual(allocate_discount(amounts, D("0.00")), amounts)


class PartLocksAndAllocation(FinanceCase):

    def test_quantity_can_rise_but_not_drop_below_the_billed_quantity(self):
        job = self.new_job()
        part = self.add_part(job, 3, 50, 100)
        self.invoice(job)
        parts.update_part(part["id"], parts.PartPatch(quantity=D("4")), REQ, user=self.user, db=self.db)
        self.db.commit()
        with self.assertRaises(AppError) as ctx:
            parts.update_part(part["id"], parts.PartPatch(quantity=D("2")), REQ, user=self.user, db=self.db)
        self.db.rollback()
        self.assertEqual(ctx.exception.code, "part_invoiced")

    def test_resending_unchanged_cost_and_price_is_not_a_change(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        self.invoice(job)
        parts.update_part(part["id"], parts.PartPatch(unit_cost=D("50"), unit_price=D("100"), notes="same values"), REQ, user=self.user, db=self.db)
        self.db.commit()

    def test_returned_units_are_taken_off_the_newest_invoice_first_and_totals_agree(self):
        job = self.new_job()
        part = self.add_part(job, 2, 50, 100)
        first = self.invoice(job)  # 2 units
        parts.update_part(part["id"], parts.PartPatch(quantity=D("3")), REQ, user=self.user, db=self.db)
        self.db.commit()
        second = self.invoice(job, supplemental=True)  # +1 unit
        self.return_part(part["id"], 2)  # two of the three billed units come back
        self.credit(second["id"], 100)
        self.credit(first["id"], 100)
        costs = {r["invoice"]: D(r["cost"]) for r in self.report("job-profit")["rows"]}
        self.assertEqual(sorted(costs.values()), [D("0.00"), D("50.00")])  # newest invoice fully reversed, oldest keeps 1 unit
        s = self.summary()
        self.assertEqual((s["parts_cost_billed"], s["parts_cost_returned"], s["direct_costs_parts"]), (D("150.00"), D("100.00"), D("50.00")))
        self.assertEqual(sum(costs.values()), s["direct_costs_parts"])


class RandomisedConsistency(FinanceCase):
    """Whatever the mix of discounts, tax, returns and credit notes, the summary and the per-job report must agree."""

    def test_summary_and_job_profit_report_always_agree(self):
        import random
        rnd = random.Random(20261119)
        for n in range(12):
            job = self.new_job()
            if rnd.random() < 0.8:
                self.add_labor(job, rnd.choice(["120.50", "300", "75.25", "999.99"]), f"Labor job {n}")
            part_ids = []
            for k in range(rnd.randint(0, 2)):
                qty = rnd.choice(["1", "2", "3.5"])
                part_ids.append((self.add_part(job, qty, rnd.choice(["10", "33.33", "120"]), rnd.choice(["20", "55.55", "200"]), f"Part {n}-{k}")["id"], D(qty)))
            if not part_ids and not self._has_labor(job):
                continue
            subtotal_guess = 50  # keep the discount below any possible subtotal
            inv = self.invoice(job, discount=rnd.choice([0, 0, "5.00", "17.17"]) if subtotal_guess else 0, tax_rate=rnd.choice(["0", "5", "15"]))
            for pid, qty in part_ids:
                if rnd.random() < 0.5:
                    self.return_part(pid, min(qty, D("1")))
            cent = D("0.01")
            if rnd.random() < 0.6:
                self.credit(inv["id"], (D(inv["total"]) / 4).quantize(cent) if D(inv["total"]) > 4 else D(inv["total"]))
            if rnd.random() < 0.5:
                outstanding = D(billing.invoice_out(self.db, self.db.get(Invoice, inv["id"]))["outstanding"])
                amount = min((D(inv["total"]) / 2).quantize(cent), outstanding)
                if amount > 0:
                    self.pay(inv["id"], amount)
        s, report = self.summary(), self.report("job-profit")
        self.assertEqual(sum(D(r["revenue"]) for r in report["rows"]), s["net_revenue_ex_tax"])
        self.assertEqual(sum(D(r["cost"]) for r in report["rows"]), s["direct_costs_parts"])
        self.assertEqual(sum(D(r["profit"]) for r in report["rows"]), s["gross_profit"])
        self.assertEqual(s["labor_net"] + s["parts_net"] + s["other_net"], s["revenue_invoiced_ex_tax"])
        self.assertEqual(s["net_tax"], s["tax_invoiced"] - s["tax_credited"])
        out = self.report("outstanding")
        self.assertEqual(sum(D(r["outstanding"]) for r in out["rows"]), s["receivables_outstanding"])

    def _has_labor(self, job):
        from app.models import RepairOperation
        return bool(self.db.scalar(select(RepairOperation.id).where(RepairOperation.visit_id == job.id).limit(1)))


class WorkflowStillWorks(FinanceCase):
    """The financial changes must not break the normal workflow or any report."""

    def test_every_report_runs_with_real_data(self):
        from app.api.reports import REPORTS
        job = self.new_job()
        self.add_labor(job, 500)
        part = self.add_part(job, 2, 50, 100)
        inv = self.invoice(job, discount=20, tax_rate="5")
        self.pay(inv["id"], 100)
        self.return_part(part["id"], 1)
        self.credit(inv["id"], 50)
        for name in REPORTS:
            data = self.report(name, customer_id=str(job.customer_id)) if name == "customer-history" else self.report(name)
            self.assertIn("rows", data, name)

    def test_report_exports_still_build_in_both_languages(self):
        from app.api.reports import export

        class ExportRequest:
            client = None
            query_params: dict = {}

        job = self.new_job()
        self.add_labor(job, 500)
        part = self.add_part(job, 2, 50, 100)
        inv = self.invoice(job, discount=20, tax_rate="5")
        self.return_part(part["id"], 1)
        self.credit(inv["id"], 50)
        for name in ("job-profit", "revenue", "outstanding"):
            for fmt in ("csv", "xlsx"):
                for lang in ("ar", "en"):
                    resp = export(name, ExportRequest(), format=fmt, lang=lang, date_from=None, date_to=None, user=self.user, db=self.db)
                    self.db.commit()
                    self.assertGreater(len(resp.body), 100, (name, fmt, lang))
        csv_text = export("job-profit", ExportRequest(), format="csv", lang="en", date_from=None, date_to=None, user=self.user, db=self.db).body.decode("utf-8-sig")
        header = csv_text.splitlines()[0]
        self.assertIn("Credit notes (excl. tax)", header)
        self.assertIn("Net revenue", header)

    def test_full_job_to_delivery_flow(self):
        from app.api import delivery, jobs as jobs_api
        from app.models import Technician
        tech = Technician(employee_no="T1", name="Technician One")
        self.db.add(tech)
        self.db.commit()
        job = self.new_job()
        op = self.add_labor(job, 400)
        part = self.add_part(job, 1, 60, 150, status="requested")
        jobs_api.update_operation(op["id"], jobs_api.OpPatch(status="done"), REQ, user=self.user, db=self.db)
        self.db.commit()
        for status in ("ordered", "purchased", "received"):
            parts.part_status(part["id"], parts.PartStatusIn(status=status), REQ, user=self.user, db=self.db)
            self.db.commit()
        parts.part_status(part["id"], parts.PartStatusIn(status="installed", technician_id=tech.id), REQ, user=self.user, db=self.db)
        self.db.commit()
        delivery.quality_check(job.id, delivery.QCIn(result="passed", repairs_verified=True, parts_verified=True, road_test_ok=True), REQ,
                               user=self.user, db=self.db)
        self.db.commit()
        inv = self.invoice(job, tax_rate="5")  # (400 + 150) * 1.05 = 577.50
        self.assertEqual(inv["total"], "577.50")
        self.pay(inv["id"], "577.50")
        out = delivery.deliver(job.id, delivery.DeliverIn(final_mileage=1000, ack_name="Customer"), REQ, user=self.user, db=self.db)
        self.db.commit()
        self.assertEqual(out["status"], "delivered")
        s = self.summary()
        self.assertEqual((s["net_revenue_ex_tax"], s["direct_costs_parts"], s["gross_profit"], s["receivables_outstanding"]),
                         (D("550.00"), D("60.00"), D("490.00"), D("0.00")))


if __name__ == "__main__":
    unittest.main()
