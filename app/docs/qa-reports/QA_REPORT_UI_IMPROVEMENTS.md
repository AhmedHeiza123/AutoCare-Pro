# UI improvements — inventory dashboard and sidebar link (2026-11-20)

Status: implemented in the package, tested on an isolated instance (temporary PostgreSQL, port 8097). **Not installed on C:\AutoCarePro.**

## What changed
**Sidebar (main app, Home page)** — the injected "Inventory & purchasing" link copied the classes of the first menu item, which is the selected one (white pill), so its pale text sat on white (measured: text rgb(220,234,255) on white). It now copies an inactive item, gets the same kind of icon as the others, and has explicit states in `integration.css`: normal, hover, keyboard focus (cyan ring), selected (teal-blue gradient, white text). A safety rule turns the text `#0B2B55` if the link ever lands on a light background.
**Inventory dashboard** — 8 KPI cards in a 4 × 2 grid (desktop ≥ 1000 px), 2 per row (tablet), 1 per row (≤ 560 px); equal heights; an icon, value and unit on each; hover lift; the whole card is a link (keyboard focus ring, aria-label). Date filter: Apply, Reset, range validation (message in place), explanatory note that balances/value are current while received/issued/purchases follow the period. New widgets: recent transactions (8), stock alerts (out of stock + low stock), monthly received vs issued (last 6 months, from the existing dashboard API), inventory value trend (only for users with cost permission).
**One new read-only API:** `GET /api/inventory/valuation-trend?months=&date_to=` (permission `inventory.costs`) — value at each month end from the append-only stock ledger (running `value_after`). No existing endpoint or formula was changed.

## Files modified
`app/frontend/inventory-src/screens-catalog.js` (dashboard), `inventory.css`, `integration.js`, `integration.css`; rebuilt `dist/assets/inventory/*` and `dist/inventory.html`/`index.html` cache-busting version; `app/backend/app/api/inventory.py` (new endpoint only); `app/backend/tests/test_mandatory_scenario.py` (1 new test).

## Tests actually executed
| Check | Result |
|---|---|
| Backend regression (all suites) | **118 run, 118 passed**, 0 failed (incl. the new trend test: last point = current valuation, 422 for months=99, 403 for storekeeper) |
| Sidebar, English and Arabic (RTL) | Inventory link readable: contrast 11.2:1; lowest of all 19 menu items 10.7:1 (minimum required 4.5:1); selected item 13:1; hover and keyboard-focus states checked on screen |
| Dashboard desktop (4×2), tablet 768 (2 per row), mobile 375 (1 per row, equal heights 161 px, no horizontal scroll) | OK, viewed in the browser |
| 8 KPI cards clicked | each opened the right screen with data (items 4, balances 4, valuation 4, low-stock 2, out-of-stock 0 rows, movements received 5, issued 1, purchases 3), no API errors |
| KPI values vs API | identical for the default and two other periods; for a period with no activity, received/issued/purchases = 0 while balances/value stay 36 / 1209.00 |
| Date validation | start after end → message, nothing sent; valid range applies; Reset returns to the default period |
| Arabic RTL layout | OK (cards right-to-left, labels, table, charts kept left-to-right) |
| Trend chart last point | 1,209 = current valuation |

## Not done / limits
* Playwright is not available on this PC; all browser checks used the built-in browser. Before/after screenshots were viewed in the session but not saved as files.
* The native date box shows the browser's own date format (not the page language); the "showing" note under it is formatted per language.
* "Stock issued (period)" is net of returns to the warehouse (existing calculation, unchanged); the dashboard now says so, so the KPI (0) can differ from the number of ISSUE rows in the movement list.
* The earlier "connection refused" lines in the browser console come from restarts of the test server during this session, not from the application.
* Not tested: other browsers, print layout of the new dashboard.
