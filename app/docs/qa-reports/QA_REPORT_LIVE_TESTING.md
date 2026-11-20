# AutoCare Pro — live-application QA, mandatory scenario (2026-11-20)

## What was and was not done
| Requested | Status |
|---|---|
| Playwright browser tests against https://localhost:8080 | **NOT EXECUTED.** The PC has no Node, no system Python and no internet, so Playwright and its browsers cannot be installed. No Playwright scripts were produced because none could be run. |
| Writing tests against the live 8080 installation | **NOT EXECUTED.** It is the installed production folder (C:\AutoCarePro). Database isolation could not be proven (the secrets file is off limits) and no test account was available to me. |
| Mandatory scenario A/B/C with the exact numbers | **EXECUTED** over real HTTP on the same code, on a throw-away PostgreSQL database (`tests/test_mandatory_scenario.py`). |
| Partial receipts, supplier balance/payment/overpay, supplier return, adjustments + reversal, insufficient stock, concurrent issue | **EXECUTED** (same file). |
| Browser pass in the built-in browser on the isolated instance (http://127.0.0.1:8097, temp PostgreSQL, DB `autocare_ui_test`, seeded demo users) | **EXECUTED 2026-11-20.** 18 main-app screens and all 13 inventory screens loaded after real login: each inventory screen rendered exactly once, no JS error, no failed API call. Real UI actions: partial goods receipt 5 of 8 (status → Partial, open 3), over-receipt of 10 refused with a message, final receipt of 3. Afterwards valuation 1221.00 (600+240+285+96 = matches), spark plug 8 @ 12 = 96.00, supplier balances Gulf 381.00 and Doha 840.00 (draft invoice excluded) — all correct. Screens not driven by hand: customers/vehicles/reception forms, quotations, invoices/payments/refunds, issue/returns/adjustments forms, role-limited views. Screenshots were viewed in the session only; they were not saved as files. |
| Second browser pass (remaining screens, same isolated instance, 2026-11-20) | **EXECUTED.** Forms driven by hand: new customer (native validation on short name/mobile, then saved); new vehicle (owner picker); 5-step check-in wizard (customer → vehicle → condition → complaint → confirm, receipt page); warehouse-part add (4 requested vs 3 available **refused**, 1 accepted, not reserved yet); new quotation, send, customer approval with evidence → **reserved 1** (on hand 3, available 2); part status Ordered → Purchased → Arrived → **issued** (on hand 2, value 190.00, reserved 0); invoice draft INV-000001 = 180.00, issue; payment 500 **refused**, 100 then 80 accepted (paid); credit note 500 **refused** (max 180), 180 accepted; refund 150 **refused** (max 100), 100 accepted (net cash 80, status overpaid = 80 still owed); stock return (empty reason refused, then unused part back to stock: on hand 3, valuation back to 1221.00, COGS 0, gross profit 0, net revenue 0); stock adjustment −20 refused, −1 accepted (spark plug 7 = 84.00, valuation 1209.00). Roles: storekeeper and technician logins — API returns 403 for money/valuation/users/audit; storekeeper menu hides Valuation; technician menu hides purchasing, receiving, adjustments, valuation, supplier balances; direct URL to valuation shows "no permission". |
| New observations (none fixed) | UI-007 (Low, compiled app): the English label of the "half" fuel level is "Text" (translation dictionary entry for the Egyptian word for half), also on the printed receipt; the stored value is correct (`half`). UI-008 (Low): two quick clicks on "New quotation" created two identical drafts (#5000, #5001) — no in-flight guard. UI-009 (Info): a warehouse-sourced part goes through Ordered/Purchased before Arrived. Note: a credit note alone does not return stock or reverse COGS (gross profit showed −95 until the part was returned) — correct by design, but staff must do both. Native confirm dialogs are auto-declined in the built-in browser, so "send quotation" needed confirm accepted by script; this is a test-tool limit, not an app defect. |
| Fixes (2026-11-20, in the package only — NOT installed on C:\AutoCarePro) | **UI-007 fixed:** dictionary entry for the Arabic fuel word "half" changed from "Text" to "Half" in the entry bundle (new file `autocare-catalog-a351a05f54f06ad0.js`, `index.html` repointed; the word is used only for the fuel level). Verified: receipt shows "Fuel: Half". **UI-008 fixed:** `inventory-src/integration.js` ignores repeat clicks (2.5 s) on "New quotation" and "Create invoice" (and their Arabic labels). Verified on the isolated instance: double-click plus a third click created exactly one new quotation (2 → 3). Frontend-only, no backend or database change; the 117 backend tests are unaffected and were not re-run. New zip: `AutoCare-Pro-Production-Inventory-2026-11-20.zip`. |
| Not driven by hand | Customer-supplied and direct-purchase tabs, purchase-invoice creation form, supplier payment form, physical count / transfer / supplier-return tabs, backup/users/settings pages beyond loading. |
| UI findings | UI-005 (Low): each navigation clears the page until data arrives, so a blank area is visible for a moment (no spinner). UI-006 (Low): the "receive more than open" error comes back in Arabic inside the English interface. Neither fixed. |

## Results
* New tests: 4. Full regression: **117 run, 117 passed, 0 failed, 0 skipped, 0 blocked** (350 s). Logs: `full_regression_117.txt`, `mandatory_scenario_run.txt`.
* No defect was found by the new tests; no code was changed in this round.

## Inventory and financial reconciliation (asserted, not estimated)
| Step | Quantity | Valuation | Other |
|---|---|---|---|
| A. buy 20 @ 30 | 20 | 600.00 | supplier owes 600.00; one GOODS_RECEIPT movement of +20 |
| B. one filter to each of 3 repair orders | 17 (issued 3) | 510.00 | parts COGS 90.00; parts billed 150.00 |
| C. one unused filter returned, credit note 50 | 18 | 540.00 | net COGS 60.00; net revenue 100.00; gross profit 40.00; ledger sum = balance |
Partial receipt: 4 then 6 of 10 (receiving 7 refused); supplier paid 50 → owes 150; paying 500 refused; supplier return 2 with credit 40 → stock 8, value 160, owes 110. Adjustment below zero refused; reversal restores stock; a movement reverses only once.

## Limits of the evidence
* The concurrency test only proves no more than one of four parallel issues succeeds for a single unit.
* Role checks, CSRF, fuzzing, uploads, periods, atomicity, backup and warranty were covered earlier (see QA_REPORT_2026-11-19.md).
* Known open issue: UI-004 (compiled app blank page on an unknown URL).

## Verdict: **PASS WITH WARNINGS** for the backend/business logic. The browser-automation part of this request was not performed.
To run it: install Playwright on a machine with Node and internet, point it at an isolated instance (set AUTOCARE_DATABASE_URL to a database whose name contains "test").
