# User manual — AutoCare Pro (English)

For workshop staff. Every step uses the icon you will see on the screen. If you get lost, press **Home** (top, next to the logo) and start again — nothing is lost.
The Arabic manual is in [USER_MANUAL_AR.md](USER_MANUAL_AR.md); both describe the same screens.

## 0) Language
Press **English / العربية** in the top bar (or on the login screen) to switch. The page reloads in the other language, and the layout flips
between right-to-left (Arabic) and left-to-right (English). Each device remembers its choice; the manager sets the default for new devices in
**Settings → General → Default system language**. Numbers and dates, printed documents and Excel/CSV exports follow the language you are using.
Names, notes and descriptions that people typed stay exactly as typed (a text typed in Arabic is not translated automatically).

## 1) Logging in
Enter your **username** and **password**, press **Log in**. After a few idle minutes the system asks you to log in again (for security).
Change your own password: click your name at the top → **Change password**.

## 2) Home screen
Large icon cards; you only see the ones for your job.

| Card | What it does |
|---|---|
| **Vehicle check-in** | Receive a vehicle and open a job card |
| **Repair tracking** | Board of every vehicle currently in the workshop |
| **Find a vehicle** | Search by plate, customer name, mobile, chassis, job number, invoice number or part number |
| **Vehicles / Register a new vehicle** | Vehicle details and history |
| **Customers / New customer** | Customer records |
| **Spare parts** | Suppliers and part search |
| **Invoices · Expenses · Accounts** | For the accountant and manager |
| **Maintenance reminders** | Vehicles that are due for service |
| **Reports** | All reports, Excel/CSV export and printing |

## 3) Vehicle check-in (5 steps)
1. **Customer** — type the name or mobile and pick the customer, or **New customer** (the system warns if a similar one exists).
2. **Vehicle** — pick the customer's vehicle or **New vehicle**.
3. **Vehicle condition** — odometer, fuel level, and mark each point **Good** or **Has a defect** (describe it). Tap 📷 to photograph a defect. You can also tap the damaged area on the **car diagram** and choose the damage type (dent, scratch, rust, crack, broken); **All OK** marks every untouched point as good. Tap any **dashboard warning lights** that are on. On the vehicle page a **health bar** (with the reasons), a mileage chart and the first photo appear at the top; in a job's inspection, **All OK** sets every item to good (green / yellow / red).
4. **Complaint** — tap the icons (brakes, oil, A/C…), add details, choose the technician and note belongings left in the car.
5. **Confirm** — review and press **Save and open the job card**. Print the **Reception receipt** and let the customer sign it.

Large buttons: **Next / Previous / Cancel**. What you typed is saved automatically even if you close the page (photos are not — retake them).
The same vehicle cannot be checked in twice while it has an open job card.

## 4) The job card (open it from the board)
- **Job status** — updates automatically as technicians are assigned, inspections recorded, quotations prepared/sent/approved, repairs progressed and parts received/installed. Finishing all active work moves the job to **Quality check**; passing the explicit quality check makes it **Ready for delivery**. Adding new work after readiness returns it to repair. You can still select a status manually; it remains until a relevant work event changes it. Each transition records its reason, and the open page checks for updates every 30 seconds. Cancellation requires a reason and delivery remains a separate confirmed action.
- **Technicians** — add more than one.
- **Repair operations** — pick the category icon → choose a ready-made item (e.g. “Replace front brake pads”) or type → hours and hourly rate (empty = the default rate from Settings). The technician presses **Start** then **Finished**.
- **Spare parts** — record the part you bought outside (name, brand, part number, supplier, supplier invoice, quantity, purchase and selling price, warranty). Then **Purchased → Arrived at the workshop → Installed** (choose who installed it). **Return** records a return. The system warns if you record the same part with the same supplier invoice twice.
- **Inspection** — choose the type and mark each item (Good / Needs attention / Critical / N/A).
- **📷 Photos and documents** — photograph or add a PDF (e.g. the supplier invoice).

## 5) Quotation and customer approval
**Quotations → New quotation** (pre-filled from the operations and parts) → adjust items/discount/tax → **Quotation sent to the customer**.
When the customer answers: tick the items, choose **Approve** or **Reject**, say **how** they agreed (WhatsApp, phone, signed paper…) and write the **evidence**. Without evidence the system will not record an approval.

## 6) Invoice and payment
**Invoices and payment → Create invoice** → review → **Issue invoice** (it cannot be edited afterwards; corrections use a credit note).
**Record payment** for any amount (partial or full) — pressing twice by mistake records it once. A **deposit** taken before the invoice counts toward it when it is issued.

## 7) Quality check and delivery
The manager ticks **I checked all the work / I checked the installed parts / I test-drove the vehicle** and presses **Pass inspection** (or **Reject** — it goes back to repair).
Under **Deliver the vehicle** the system lists what is missing in red (unfinished operation, part not installed, quality check, invoice, balance due). When everything is green, enter the odometer and the receiver's name and press **Deliver the vehicle**, then print the **Delivery report**.
Only a manager can deliver with something missing, and must write the reason; it is recorded.

## 8) Vehicle history
Open the vehicle (search → the vehicle): the **Vehicle history** lists every visit, newest first; click a visit for all its details (parts, technician, warranty, invoice, photos). Filter by service type or odometer, print with 🖨.
History is never erased — previous owners and previous plates are kept. A **QR code** opens the vehicle page (login required).

## 9) Warranty and reminders
Warranty is created automatically when you install a part that has a warranty period; labour warranty can be added. **Record a warranty claim** (the manager decides).
After delivery the system creates **reminders** (e.g. oil change in 6 months or 5,000 km). Open **Maintenance reminders** and call the customer.

## 10) Tips
- A red message explains the problem in plain words. Read it.
- Status is never colour only: every status has an icon and a word (✔ ready, ⏳ waiting, ✖ problem).
- If you see “The record was changed by another user”, refresh the page and repeat.
- “The system is under maintenance” means the manager is restoring a backup; wait a few minutes and refresh.
