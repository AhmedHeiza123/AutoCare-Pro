"""Reports: JSON for the screen plus CSV / Excel exports. Every figure is computed from the underlying transactions."""
import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.billing import ZERO, money_state, money_states
from app.api.settings_api import format_number
from app.api.deps import client_ip, current_user
from app.core.audit import audit
from app.core.en_text import EN
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (PartReturn, Customer, Expense, ExpenseCategory, Invoice, InvoiceItem, JobStatusHistory, PartPurchase, Payment,
                        QualityCheck, Refund, RepairOperation, Supplier, Technician, TechnicianAssignment, Vehicle,
                        VehicleVisit, Warranty, WarrantyClaim)
from app.models.auth import User
from app.services import settings as svc_settings
from app.services.pricing import line_cost, line_price, returned_map
from app.services.templates import CLOSED

router = APIRouter(prefix="/api", tags=["reports"])
TZ = ZoneInfo("Asia/Qatar")
Col = tuple[str, str, str]  # key, Arabic label, type: text|int|money|date|datetime


def rng(d_from: date | None, d_to: date | None) -> tuple[date, date, datetime, datetime]:
    today = datetime.now(TZ).date()
    a, b = d_from or today.replace(day=1), d_to or today
    if b < a:
        raise AppError("تاريخ النهاية قبل البداية", 422, "bad_range")
    return a, b, datetime.combine(a, time.min, TZ), datetime.combine(b + timedelta(days=1), time.min, TZ)


def s(v: Decimal | int | None) -> str:
    return f"{Decimal(v or 0):.2f}"


def local(dt: datetime | None) -> str | None:
    return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M") if dt else None


def veh_label(v: Vehicle) -> str:
    return f"{v.make} {v.model}"


class Ctx:
    def __init__(self, db: DbSession, user: User, a: date, b: date, start: datetime, end: datetime, params: dict):
        self.db, self.user, self.a, self.b, self.start, self.end, self.p = db, user, a, b, start, end, params

    @property
    def costs(self) -> bool:
        return "parts.costs" in self.user.permissions


# ---- operational reports ------------------------------------------------------------------
def r_activity(c: Ctx):
    group = c.p.get("group", "day")
    if group not in ("day", "week", "month"):
        raise AppError("تجميع غير صحيح", 422, "bad_group")

    def key(dt: datetime) -> str:
        d = dt.astimezone(TZ)
        return d.strftime("%Y-%m-%d") if group == "day" else (f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}" if group == "week" else d.strftime("%Y-%m"))

    rows: dict[str, dict] = defaultdict(lambda: {"received": 0, "delivered": 0, "invoices": 0, "revenue": ZERO, "cash": ZERO})
    for v in c.db.scalars(select(VehicleVisit).where(VehicleVisit.arrival_at >= c.start, VehicleVisit.arrival_at < c.end)):
        rows[key(v.arrival_at)]["received"] += 1
    for v in c.db.scalars(select(VehicleVisit).where(VehicleVisit.delivered_at >= c.start, VehicleVisit.delivered_at < c.end)):
        rows[key(v.delivered_at)]["delivered"] += 1
    for i in c.db.scalars(select(Invoice).where(Invoice.status == "issued", Invoice.issued_at >= c.start, Invoice.issued_at < c.end)):
        r = rows[key(i.issued_at)]
        r["invoices"] += 1
        r["revenue"] += Decimal(i.subtotal) - Decimal(i.discount)
    for p in c.db.scalars(select(Payment).where(Payment.paid_at >= c.start, Payment.paid_at < c.end)):
        rows[key(p.paid_at)]["cash"] += Decimal(p.amount)
    for rf in c.db.scalars(select(Refund).where(Refund.refunded_at >= c.start, Refund.refunded_at < c.end)):
        rows[key(rf.refunded_at)]["cash"] -= Decimal(rf.amount)
    cols: list[Col] = [("period", "الفترة", "text"), ("received", "عربيات مستلمة", "int"), ("delivered", "عربيات مسلّمة", "int"),
                       ("invoices", "فواتير", "int"), ("revenue", "الإيراد (بدون ضريبة)", "money"), ("cash", "صافي النقدية", "money")]
    return cols, [{"period": k, **{kk: (s(vv) if isinstance(vv, Decimal) else vv) for kk, vv in v.items()}} for k, v in sorted(rows.items())]


def _visit_rows(c: Ctx, where, extra=None):
    q = select(VehicleVisit, Vehicle, Customer.full_name).join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id) \
        .join(Customer, Customer.id == VehicleVisit.customer_id).where(*where)
    out = []
    now = datetime.now(timezone.utc)
    techs: dict = defaultdict(list)
    for vid, n in c.db.execute(select(TechnicianAssignment.visit_id, Technician.name).join(Technician, Technician.id == TechnicianAssignment.technician_id)):
        techs[vid].append(n)
    for j, v, cust in c.db.execute(q.order_by(VehicleVisit.arrival_at)):
        out.append({"job_no": j.visit_no, "arrival": local(j.arrival_at), "delivered": local(j.delivered_at), "plate": v.plate,
                    "vehicle": veh_label(v), "customer": cust, "mileage": j.mileage, "category": j.category, "status": j.status,
                    "technicians": "، ".join(techs.get(j.id, [])), "days": (((j.delivered_at or now) - j.arrival_at).days),
                    "expected": local(j.expected_completion_at), "total": s(j.total_cost)})
    return out


def r_received(c: Ctx):
    cols: list[Col] = [("job_no", "رقم الأمر", "int"), ("arrival", "وقت الاستلام", "text"), ("plate", "اللوحة", "text"), ("vehicle", "العربية", "text"),
                       ("customer", "العميل", "text"), ("mileage", "العداد", "int"), ("category", "الفئة", "text"), ("status", "الحالة", "text")]
    return cols, _visit_rows(c, [VehicleVisit.arrival_at >= c.start, VehicleVisit.arrival_at < c.end])


def r_delivered(c: Ctx):
    cols: list[Col] = [("job_no", "رقم الأمر", "int"), ("delivered", "وقت التسليم", "text"), ("plate", "اللوحة", "text"), ("vehicle", "العربية", "text"),
                       ("customer", "العميل", "text"), ("days", "أيام في الورشة", "int"), ("total", "إجمالي الأمر", "money")]
    return cols, _visit_rows(c, [VehicleVisit.delivered_at >= c.start, VehicleVisit.delivered_at < c.end])


def r_open(c: Ctx):
    cols: list[Col] = [("job_no", "رقم الأمر", "int"), ("plate", "اللوحة", "text"), ("vehicle", "العربية", "text"), ("customer", "العميل", "text"),
                       ("status", "الحالة", "text"), ("technicians", "الفنيون", "text"), ("days", "أيام في الورشة", "int"), ("expected", "التسليم المتوقع", "text")]
    return cols, _visit_rows(c, [VehicleVisit.status.notin_(CLOSED)])


def r_delayed(c: Ctx):
    cols, rows = r_open(c)
    now = local(datetime.now(timezone.utc))
    return cols, [r for r in rows if r["expected"] and r["expected"] < now]


def r_categories(c: Ctx):
    q = select(RepairOperation.category, func.count(RepairOperation.id), func.coalesce(func.sum(RepairOperation.labor_hours), 0),
               func.coalesce(func.sum(RepairOperation.labor_amount), 0)) \
        .join(VehicleVisit, VehicleVisit.id == RepairOperation.visit_id) \
        .where(VehicleVisit.arrival_at >= c.start, VehicleVisit.arrival_at < c.end, RepairOperation.status != "cancelled") \
        .group_by(RepairOperation.category).order_by(func.count(RepairOperation.id).desc())
    cols: list[Col] = [("category", "الفئة", "text"), ("ops", "عدد العمليات", "int"), ("hours", "ساعات العمل", "money"), ("labor", "الأجور", "money")]
    return cols, [{"category": cat or "بدون فئة", "ops": n, "hours": s(h), "labor": s(l)} for cat, n, h, l in c.db.execute(q)]


def r_technicians(c: Ctx):
    rows = []
    for t in c.db.scalars(select(Technician).order_by(Technician.name)):
        jobs = list(c.db.scalars(select(VehicleVisit.id).join(TechnicianAssignment, TechnicianAssignment.visit_id == VehicleVisit.id)
                                 .where(TechnicianAssignment.technician_id == t.id, VehicleVisit.arrival_at >= c.start, VehicleVisit.arrival_at < c.end)))
        ops = list(c.db.scalars(select(RepairOperation).where(RepairOperation.technician_id == t.id, RepairOperation.status == "done",
                                                              RepairOperation.ended_at >= c.start, RepairOperation.ended_at < c.end)))
        qcs = list(c.db.scalars(select(QualityCheck).where(QualityCheck.visit_id.in_(jobs)))) if jobs else []
        failed = sum(1 for q in qcs if q.result == "failed")
        rows.append({"name": t.name, "jobs": len(jobs), "ops_done": len(ops), "hours": s(sum((Decimal(o.labor_hours) for o in ops), ZERO)),
                     "labor": s(sum((Decimal(o.labor_amount) for o in ops), ZERO)), "rework": failed,
                     "qc_pass_rate": f"{(100 * (len(qcs) - failed) // len(qcs)) if qcs else 100}%"})
    cols: list[Col] = [("name", "الفني", "text"), ("jobs", "أوامر مسندة", "int"), ("ops_done", "عمليات منتهية", "int"), ("hours", "ساعات العمل", "money"),
                       ("labor", "قيمة الأجور", "money"), ("rework", "حالات إعادة تصليح", "int"), ("qc_pass_rate", "نسبة اجتياز الجودة", "text")]
    return cols, rows


def r_parts(c: Ctx):
    cols: list[Col] = [("date", "التاريخ", "text"), ("job_no", "أمر", "int"), ("plate", "اللوحة", "text"), ("part", "القطعة", "text"), ("brand", "الماركة", "text"),
                       ("number", "رقم القطعة", "text"), ("supplier", "المورد", "text"), ("qty", "الكمية", "money"), ("price", "سعر البيع", "money"), ("status", "الحالة", "text")]
    if c.costs:
        cols += [("cost", "التكلفة", "money"), ("profit", "الربح", "money")]
    rows = []
    ret = returned_map(c.db)
    q = select(PartPurchase, VehicleVisit.visit_no, Vehicle.plate, Supplier.name).join(VehicleVisit, VehicleVisit.id == PartPurchase.visit_id) \
        .join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id).outerjoin(Supplier, Supplier.id == PartPurchase.supplier_id) \
        .where(func.coalesce(PartPurchase.purchased_at, PartPurchase.created_at) >= c.start, func.coalesce(PartPurchase.purchased_at, PartPurchase.created_at) < c.end) \
        .order_by(PartPurchase.id)
    for p, no, plate, sup in c.db.execute(q):
        r = {"date": local(p.purchased_at or p.created_at), "job_no": no, "plate": plate, "part": p.part_name, "brand": p.brand, "number": p.part_number,
             "supplier": sup, "qty": s(p.quantity), "price": s(line_price(c.db, p, ret)), "status": p.status}
        if c.costs:
            r["cost"], r["profit"] = s(line_cost(c.db, p, ret)), s(line_price(c.db, p, ret) - line_cost(c.db, p, ret))
        rows.append(r)
    return cols, rows


def r_suppliers(c: Ctx):
    rows = []
    ret = returned_map(c.db)
    for sup in c.db.scalars(select(Supplier).order_by(Supplier.name)):
        parts = list(c.db.scalars(select(PartPurchase).where(PartPurchase.supplier_id == sup.id,
                                                             func.coalesce(PartPurchase.purchased_at, PartPurchase.created_at) >= c.start,
                                                             func.coalesce(PartPurchase.purchased_at, PartPurchase.created_at) < c.end)))
        if not parts:
            continue
        refunds = to_money(c.db.scalar(select(func.coalesce(func.sum(PartReturn.refund_amount), 0)).where(PartReturn.part_id.in_([p.id for p in parts]))))
        rows.append({"supplier": sup.name, "parts": len(parts), "cost": s(sum((line_cost(c.db, p, ret) for p in parts), ZERO)), "refunds": s(refunds)})
    cols: list[Col] = [("supplier", "المورد", "text"), ("parts", "عدد القطع", "int"), ("cost", "إجمالي المشتريات", "money"), ("refunds", "المرتجعات المستردة", "money")]
    return cols, rows


# ---- financial reports ----------------------------------------------------------------------------
def r_revenue(c: Ctx):
    rows = []
    for i, cust in c.db.execute(select(Invoice, Customer.full_name).join(Customer, Customer.id == Invoice.customer_id)
                                .where(Invoice.status == "issued", Invoice.issued_at >= c.start, Invoice.issued_at < c.end).order_by(Invoice.invoice_no)):
        st = money_state(c.db, i)
        rows.append({"number": format_number(c.db, "invoice", i.invoice_no), "date": local(i.issued_at), "customer": cust, "subtotal": s(i.subtotal), "discount": s(i.discount),
                     "revenue": s(Decimal(i.subtotal) - Decimal(i.discount)), "tax": s(i.tax_amount), "total": s(i.total), "paid": s(st["net_paid"]), "outstanding": s(st["outstanding"])})
    cols: list[Col] = [("number", "رقم الفاتورة", "text"), ("date", "التاريخ", "text"), ("customer", "العميل", "text"), ("subtotal", "الإجمالي", "money"),
                       ("discount", "الخصم", "money"), ("revenue", "الإيراد (بدون ضريبة)", "money"), ("tax", "الضريبة", "money"), ("total", "الصافي", "money"),
                       ("paid", "المدفوع", "money"), ("outstanding", "المتبقي", "money")]
    return cols, rows


def r_payments(c: Ctx):
    rows = []
    q = select(Payment, VehicleVisit.visit_no, Customer.full_name).join(VehicleVisit, VehicleVisit.id == Payment.visit_id) \
        .join(Customer, Customer.id == VehicleVisit.customer_id).where(Payment.paid_at >= c.start, Payment.paid_at < c.end).order_by(Payment.id)
    for p, no, cust in c.db.execute(q):
        refunded = to_money(c.db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.payment_id == p.id)))
        rows.append({"date": local(p.paid_at), "job_no": no, "customer": cust, "kind": p.kind, "method": p.method, "amount": s(p.amount), "refunded": s(refunded), "net": s(Decimal(p.amount) - refunded)})
    cols: list[Col] = [("date", "التاريخ", "text"), ("job_no", "أمر", "int"), ("customer", "العميل", "text"), ("kind", "النوع", "text"), ("method", "الطريقة", "text"),
                       ("amount", "المبلغ", "money"), ("refunded", "المسترد", "money"), ("net", "الصافي", "money")]
    return cols, rows


def r_outstanding(c: Ctx):
    rows = []
    now = datetime.now(timezone.utc)
    found = list(c.db.execute(select(Invoice, Customer.full_name, Customer.mobile).join(Customer, Customer.id == Invoice.customer_id)
                              .where(Invoice.status == "issued").order_by(Invoice.invoice_no)))
    states = money_states(c.db, [i for i, _, _ in found])
    fin = svc_settings.get_section(c.db, "finance")
    for i, cust, mobile in found:
        st = states[i.id]
        if st["outstanding"] > 0:
            rows.append({"number": f"{fin['invoice_prefix']}-{i.invoice_no:0{int(fin['number_width'])}d}", "customer": cust, "mobile": mobile, "total": s(st["due"]), "paid": s(st["net_paid"]),
                         "outstanding": s(st["outstanding"]), "age": (now - i.issued_at).days})
    cols: list[Col] = [("number", "رقم الفاتورة", "text"), ("customer", "العميل", "text"), ("mobile", "الموبايل", "text"), ("total", "المستحق", "money"),
                       ("paid", "المدفوع", "money"), ("outstanding", "المتبقي", "money"), ("age", "عمر الدين (يوم)", "int")]
    return cols, rows


def r_expenses(c: Ctx):
    rows = [{"date": e.expense_date.isoformat(), "category": cat, "description": e.description, "payee": e.payee, "amount": s(e.amount)}
            for e, cat in c.db.execute(select(Expense, ExpenseCategory.name).join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
                                       .where(Expense.is_void.is_(False), Expense.expense_date >= c.a, Expense.expense_date <= c.b)
                                       .order_by(Expense.expense_date, Expense.id))]
    cols: list[Col] = [("date", "التاريخ", "text"), ("category", "النوع", "text"), ("description", "البيان", "text"), ("payee", "المدفوع له", "text"), ("amount", "المبلغ", "money")]
    return cols, rows


def r_profit(c: Ctx):
    rows = []
    for i, no, plate in c.db.execute(select(Invoice, VehicleVisit.visit_no, Vehicle.plate).join(VehicleVisit, VehicleVisit.id == Invoice.visit_id)
                                     .join(Vehicle, Vehicle.id == Invoice.vehicle_id)
                                     .where(Invoice.status == "issued", Invoice.issued_at >= c.start, Invoice.issued_at < c.end).order_by(Invoice.invoice_no)):
        items = list(c.db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == i.id)))
        labor = sum((Decimal(x.amount) for x in items if x.kind == "labor"), ZERO)
        parts_rev = sum((Decimal(x.amount) for x in items if x.kind == "part"), ZERO)
        other = sum((Decimal(x.amount) for x in items if x.kind == "other"), ZERO)
        cost = ZERO
        for x in items:
            if x.part_id:
                p = c.db.get(PartPurchase, x.part_id)
                cost += to_money(Decimal(x.quantity) * Decimal(p.unit_cost))
        revenue = Decimal(i.subtotal) - Decimal(i.discount)
        rows.append({"job_no": no, "invoice": format_number(c.db, "invoice", i.invoice_no), "plate": plate, "labor": s(labor), "parts": s(parts_rev), "other": s(other),
                     "discount": s(i.discount), "revenue": s(revenue), "cost": s(cost), "profit": s(revenue - cost)})
    cols: list[Col] = [("job_no", "أمر", "int"), ("invoice", "فاتورة", "text"), ("plate", "اللوحة", "text"), ("labor", "أجور", "money"), ("parts", "قطع", "money"),
                       ("other", "أخرى", "money"), ("discount", "الخصم", "money"), ("revenue", "الإيراد", "money"), ("cost", "تكلفة القطع", "money"), ("profit", "مجمل الربح", "money")]
    return cols, rows


def r_customer(c: Ctx):
    cid = c.p.get("customer_id")
    if not cid:
        raise AppError("اختر العميل", 422, "customer_required")
    cust = c.db.get(Customer, cid)
    if not cust:
        raise AppError("العميل غير موجود", 404, "not_found")
    rows = []
    for j, v in c.db.execute(select(VehicleVisit, Vehicle).join(Vehicle, Vehicle.id == VehicleVisit.vehicle_id)
                             .where(VehicleVisit.customer_id == cust.id).order_by(VehicleVisit.arrival_at)):
        invoices = list(c.db.scalars(select(Invoice).where(Invoice.visit_id == j.id, Invoice.status == "issued")))
        states = [money_state(c.db, inv) for inv in invoices]
        rows.append({"job_no": j.visit_no, "date": local(j.arrival_at), "plate": v.plate, "vehicle": veh_label(v), "category": j.category, "status": j.status,
                     "invoiced": s(sum((i.total for i in invoices), ZERO)), "paid": s(sum((st["net_paid"] for st in states), ZERO)), "outstanding": s(sum((st["outstanding"] for st in states), ZERO))})
    cols: list[Col] = [("job_no", "أمر", "int"), ("date", "التاريخ", "text"), ("plate", "اللوحة", "text"), ("vehicle", "العربية", "text"), ("category", "الفئة", "text"),
                       ("status", "الحالة", "text"), ("invoiced", "المفوتر", "money"), ("paid", "المدفوع", "money"), ("outstanding", "المتبقي", "money")]
    return cols, rows


def r_claims(c: Ctx):
    rows = []
    for cl, w, v in c.db.execute(select(WarrantyClaim, Warranty, Vehicle).join(Warranty, Warranty.id == WarrantyClaim.warranty_id)
                                 .join(Vehicle, Vehicle.id == Warranty.vehicle_id).where(WarrantyClaim.claim_date >= c.a, WarrantyClaim.claim_date <= c.b)
                                 .order_by(WarrantyClaim.id)):
        rows.append({"date": cl.claim_date.isoformat(), "plate": v.plate, "vehicle": veh_label(v), "warranty": w.description, "problem": cl.description,
                     "status": cl.status, "resolution": cl.resolution})
    cols: list[Col] = [("date", "تاريخ المطالبة", "text"), ("plate", "اللوحة", "text"), ("vehicle", "العربية", "text"), ("warranty", "الضمان", "text"),
                       ("problem", "المشكلة", "text"), ("status", "الحالة", "text"), ("resolution", "القرار", "text")]
    return cols, rows


def r_repeat(c: Ctx):
    window = int(c.p.get("days", 90))
    by: dict[tuple, list[VehicleVisit]] = defaultdict(list)
    for j in c.db.scalars(select(VehicleVisit).where(VehicleVisit.category.is_not(None), VehicleVisit.status != "cancelled").order_by(VehicleVisit.arrival_at)):
        by[(j.vehicle_id, j.category)].append(j)
    rows = []
    for (vid, cat), visits in by.items():
        for prev, cur in zip(visits, visits[1:]):
            gap = (cur.arrival_at - prev.arrival_at).days
            if gap <= window and c.start <= cur.arrival_at < c.end:
                v = c.db.get(Vehicle, vid)
                rows.append({"plate": v.plate, "vehicle": veh_label(v), "category": cat, "first_job": prev.visit_no, "repeat_job": cur.visit_no, "gap_days": gap})
    cols: list[Col] = [("plate", "اللوحة", "text"), ("vehicle", "العربية", "text"), ("category", "الفئة", "text"), ("first_job", "الأمر الأول", "int"),
                       ("repeat_job", "الأمر المتكرر", "int"), ("gap_days", "الأيام بينهما", "int")]
    return cols, rows


FIN = "reports.financial"
REPORTS: dict[str, tuple[str, str, object]] = {  # name: (title, permission, fn)
    "activity": ("النشاط اليومي / الأسبوعي / الشهري", FIN, r_activity),
    "received": ("العربيات المستلمة", "visits.read", r_received),
    "delivered": ("العربيات المسلّمة", "visits.read", r_delivered),
    "open-jobs": ("الأوامر المفتوحة", "visits.read", r_open),
    "delayed-jobs": ("الأوامر المتأخرة", "visits.read", r_delayed),
    "repair-categories": ("فئات الصيانة", "visits.read", r_categories),
    "technicians": ("إنتاجية الفنيين", "visits.read", r_technicians),
    "parts": ("مشتريات قطع الغيار", "visits.read", r_parts),
    "suppliers": ("مشتريات الموردين", FIN, r_suppliers),
    "revenue": ("الإيرادات", FIN, r_revenue),
    "payments": ("المدفوعات", FIN, r_payments),
    "outstanding": ("المتبقي عند العملاء", FIN, r_outstanding),
    "expenses": ("المصروفات", FIN, r_expenses),
    "job-profit": ("ربحية الأوامر", FIN, r_profit),
    "customer-history": ("تاريخ العميل", "billing.read", r_customer),
    "warranty-claims": ("مطالبات الضمان", "visits.read", r_claims),
    "repeat-repairs": ("الصيانة المتكررة", "visits.read", r_repeat),
}
SUMMABLE = {"money", "int"}
NO_SUM = {"job_no", "mileage", "first_job", "repeat_job", "age", "gap_days", "days"}


def run(name: str, db: DbSession, user: User, d_from, d_to, params: dict) -> dict:
    if name not in REPORTS:
        raise AppError("تقرير غير معروف", 404, "not_found")
    title, perm, fn = REPORTS[name]
    if perm not in user.permissions:
        raise AppError("ليس لديك صلاحية لهذا التقرير", 403, "forbidden")
    a, b, start, end = rng(d_from, d_to)
    cols, rows = fn(Ctx(db, user, a, b, start, end, params))
    totals = {}
    for key, _, typ in cols:
        if typ in SUMMABLE and key not in NO_SUM:
            totals[key] = s(sum((Decimal(str(r[key])) for r in rows if r.get(key) not in (None, "")), Decimal(0))) if typ == "money" else sum(int(r[key]) for r in rows if r.get(key) not in (None, ""))
    return {"name": name, "title": title, "date_from": a, "date_to": b, "columns": [{"key": k, "label": l, "type": t} for k, l, t in cols],
            "rows": rows, "totals": totals, "count": len(rows)}


@router.get("/reports")
def catalogue(user: User = Depends(current_user)):
    return [{"name": n, "title": t} for n, (t, perm, _) in REPORTS.items() if perm in user.permissions]


@router.get("/reports/{name}")
def report(name: str, request: Request, date_from: date | None = None, date_to: date | None = None,
           user: User = Depends(current_user), db: DbSession = Depends(get_db, scope="function")):
    extra = {k: v for k, v in request.query_params.items() if k not in ("date_from", "date_to")}
    return run(name, db, user, date_from, date_to, extra)


@router.get("/reports/{name}/export")
def export(name: str, request: Request, format: str = Query("xlsx", pattern="^(xlsx|csv)$"), lang: str = Query("ar", pattern="^(ar|en)$"),
           date_from: date | None = None, date_to: date | None = None, user: User = Depends(current_user), db: DbSession = Depends(get_db, scope="function")):
    extra = {k: v for k, v in request.query_params.items() if k not in ("date_from", "date_to", "format", "lang")}
    data = run(name, db, user, date_from, date_to, extra)
    en = lang == "en"
    tr = (lambda s: EN.get(s, s) if isinstance(s, str) else s) if en else (lambda s: s)  # English headers/labels for English users
    total_label = tr("الإجمالي")
    period = EN["من {0} إلى {1}"].format(data["date_from"], data["date_to"]) if en else f"من {data['date_from']} إلى {data['date_to']}"
    data["title"] = tr(data["title"])
    data["rows"] = [{k: tr(v) for k, v in r.items()} for r in data["rows"]]
    headers = [tr(c["label"]) for c in data["columns"]]
    keys = [c["key"] for c in data["columns"]]
    audit(db, user, "report.export", "report", name, after={"format": format, "rows": data["count"]}, ip=client_ip(request))
    fname = f"AutoCarePro_{name}_{data['date_from']}_{data['date_to']}.{format}"
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        for r in data["rows"]:
            w.writerow([_safe(r.get(k)) for k in keys])
        if data["totals"]:
            w.writerow([total_label] + [data["totals"].get(k, "") for k in keys[1:]])
        body = "﻿" + buf.getvalue()  # BOM so Excel opens Arabic text correctly
        return Response(body.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    wb = Workbook()
    ws = wb.active
    ws.title = data["title"][:30]
    ws.sheet_view.rightToLeft = not en
    ws.append([data["title"]])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([period])
    ws.append(headers)
    for cell in ws[3]:
        cell.font, cell.alignment = Font(bold=True), Alignment(horizontal="center")
    for r in data["rows"]:
        ws.append([_cell(r.get(k), c["type"]) for k, c in zip(keys, data["columns"])])
    if data["totals"]:
        ws.append([total_label] + [_cell(data["totals"].get(k), c["type"]) if k in data["totals"] else None for k, c in zip(keys[1:], data["columns"][1:])])
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)
    for i, h in enumerate(headers, 1):
        ws.column_dimensions[chr(64 + i) if i < 27 else "AA"].width = max(14, len(h) + 4)
    out = io.BytesIO()
    wb.save(out)
    return Response(out.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


def _safe(v):
    """Neutralise spreadsheet formula injection in exported text."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return "'" + v
    return v


def _cell(v, typ):
    if v in (None, ""):
        return None
    if typ == "money":
        return float(Decimal(str(v)))  # numeric cell for Excel (display only; all stored amounts remain Decimal)
    if typ == "int":
        return int(v)
    return _safe(v)
