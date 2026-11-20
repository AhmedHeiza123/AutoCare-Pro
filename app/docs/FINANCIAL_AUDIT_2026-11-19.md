# AutoCare Pro — Financial Audit & Bug Fixes (2026-11-19)

Scope: spare-parts cost, invoices (discounts, tax, payments, refunds, credit notes), revenue allocation, profitability, financial
reporting and data integrity. Method: read the code, model and migrations; formulate hypotheses; **reproduce each on a throw-away
PostgreSQL before changing anything**; fix minimally; add regression tests. Production data was never touched (no migration, no
data change, tests run on a separate temporary server on another port).

## 1. Confirmed bugs

| # | Bug | Root cause | Evidence (before → after) |
|---|-----|-----------|---------------------------|
| 1 | **Invoice from a quotation ignored the quotation's discount** — customer billed more than they approved | `create_invoice` set `discount = body.discount or 0` and never read `quote.discount` (tax rate *was* carried) | Quote 945.00 → invoice discount 0.00, total **1050.00**; now discount 100.00, total **945.00**. Partial approval (labor 600 of 1000) → 600.00 / 0.00 → now 540.00 (discount prorated 60.00) |
| 2 | **Revenue categories did not reflect the invoice discount** (Labor + Parts + Other ≠ revenue) | `financial_summary` returned gross category sums next to discounted revenue, with no allocation | Labor 600 + Parts 400 = 1000.00 shown vs revenue 900.00 → now `labor_net` 540.00 + `parts_net` 360.00 = 900.00 (pro-rata, rounding cent kept in the largest category; sum always exact) |
| 3 | **COGS ignored returns of billed parts** → profit understated | COGS = billed qty × cost, never reduced when units go back to the supplier (credit note reduced revenue only) | Part 2 × (cost 50, price 100), 1 returned + credit 100: net revenue 100, COGS **100**, gross profit **0.00** → COGS **50**, gross profit **50.00** |
| 4 | **Job-profit report ignored credit notes and returned parts**; it disagreed with the summary | `r_profit` used gross revenue and gross item cost | Row revenue/cost/profit 200/100/**100** vs summary 0 → 100/50/**50**; Σ job profit = summary gross profit (new regression test) |
| 5 | **Historical cost/price could change after invoicing** | `update_part` allowed `unit_cost`/`unit_price`/quantity changes on a part already on an issued invoice | unit_cost 50→80 accepted, COGS of an *old* invoice 100.00 → 160.00; now rejected (`part_invoiced`) |
| 6 | **A billed part could be cancelled** → revenue with no part/cost | `part_status` had no billing check | cancel allowed → now rejected (`part_invoiced`) |
| 7 | VAT reporting did not show tax reversed by credit notes | only `tax_invoiced` existed | now `tax_credited` and `net_tax` (1050 invoice, 105 credit → tax 50, credited 5, net 45) |

## 2. Files changed
* `backend/app/services/accounting.py` (new): discount allocation, billed quantity, COGS return rules.
* `backend/app/api/billing.py`: quotation discount carried (pro rata to billed items).
* `backend/app/api/parts.py`: lock cost/price/qty-decrease and cancellation once billed (quantity increases and notes stay allowed; resending unchanged values is not a change).
* `backend/app/api/finance.py`: summary — net categories, net COGS, tax credited. **Existing API keys unchanged** (`labor_billed`, `parts_billed`, `direct_costs_parts`… keep their names; `direct_costs_parts` is now net of returns). New keys: `discount_invoiced`, `labor_net`, `parts_net`, `other_net`, `tax_credited`, `net_tax`, `parts_cost_billed`, `parts_cost_returned`.
* `backend/app/api/reports.py`: job-profit net of credit notes/returns (+ new column "credit notes excl. tax", English label added).
* Front end (built bundle only, no source in the install): financial summary page shows the net categories, credited VAT and the returns note; falls back to the old keys, so it also works with an old server.
* `backend/tests/` (new): harness, 35 tests, `run_tests.ps1` (one command, temporary database, cleans up, refuses non-"test" databases).

## 3. Accounting rules now enforced
* Discount is invoice-level and spread pro rata over Labor/Parts/Other. Credit notes reduce revenue (ex-tax) in the period they are issued.
* COGS = cost of parts on issued invoices in the period − cost of **already-billed** units returned in the period. Returns of never-billed units do not change COGS (they were never expensed). Per invoice, returned units are taken off the newest invoice first.
* Gross profit = net revenue − net COGS (labor has no recorded cost). Net profit = gross profit − recorded operating expenses.

## 4. Verified correct (no change needed)
Invoice totals ((subtotal − discount) × tax), half-up rounding, partial payment / overpayment rejection, refunds capped to the payment, credit notes capped to the invoice and reversible, deposit application to the first issued invoice and single counting in cash, receivables = total − credits − net paid, SQL `payment_status` filter equals the Python state, draft/cancelled invoices excluded from revenue, voided expenses excluded, supplemental invoices never bill the same part twice, rounding with many fractional lines, full job → QC → invoice → payment → delivery flow, every report and the CSV/XLSX exports (Arabic and English).

## 5. Tests executed (real PostgreSQL 15, temporary server)
`run_tests.ps1` → **Ran 35 tests … OK** (run twice; the last run is after the final edit). Before the fixes, 10 of the first 20 tests failed: 8 on genuine bugs (1–4, 5, 7) and 2 because of mistakes in the test code itself (corrected before the fixes were written); bug 6 was reproduced by a later probe test. Identical scenarios were also run against the pre-audit code (the package made earlier the same day) and the current code to produce the before/after numbers above. Includes a seeded randomised test: for 12 random jobs (discounts, tax 0/5/15 %, returns, credit notes, payments) the summary and the job-profit report agree to the cent, and categories add up to revenue. Safety guard verified: with no variable or a database not named "test", the tests are skipped and never connect.

## 6. Remaining risks / decisions for the owner
1. **The web UI creates invoices from the job's work and does not send a quotation**, so a quotation discount only applies through the API path fixed here. Decide whether the UI should pass `quotation_id` (or prompt for the discount).
2. Parts the customer **rejected** in a quotation can still be billed through a supplemental invoice unless the part is cancelled (workflow, not arithmetic).
3. Cancelling an invoice removes its revenue from the period it was issued (periods are restated, not adjusted in the cancellation period).
4. Manual invoice lines of kind "part" without a linked part have **zero cost** (profit overstated); labor cost is not modeled at all.
5. COGS reversal uses `unit_cost × units`; the supplier `refund_amount` (restocking fees, partial refunds) is not used in profit.
6. Parts can be billed while still "requested" (not yet purchased); cost is recognised at billing, not at purchase.
7. Customer deposits / overpayments are not reported as a liability, and overpayment on one invoice does not offset another (by design, documented in delivery rules).
8. Refunds and credit notes have no idempotency key (a double click could register two).
9. Reports for past periods that contain returns of billed parts will now show a different (more correct) COGS/profit than before; stored records are unchanged.
10. Time zone is fixed to Asia/Qatar.

## 7. How to re-run
`powershell -ExecutionPolicy Bypass -File C:\AutoCarePro\backend\tests\run_tests.ps1` (normal window, ~1.5 min).
The running service must be restarted (`Restart-Service AutoCarePro`) to load the backend changes.
