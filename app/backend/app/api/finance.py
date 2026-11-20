"""Operating expenses (void, never delete) and the financial summary report."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.billing import ZERO, money_states
from app.services import purchasing as pur
from app.services.accounting import allocate_discount, cogs_returned_in_period
from app.api.deps import client_ip, require
from app.core.audit import audit
from app.services import settings as cfg
from app.core.dates import next_day_start
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (CreditNote, Expense, ExpenseCategory, InventoryBalance, Invoice, InvoiceItem, PartPurchase, Payment,
                        PurchaseInvoice, Refund, StockMovement, SupplierPayment)
from app.models.auth import User

router = APIRouter(prefix="/api", tags=["finance"])
TZ = ZoneInfo("Asia/Qatar")
DEFAULT_CATEGORIES = ["مرافق (كهرباء ومياه)", "إيجار", "صيانة معدات", "خدمات خارجية", "رواتب", "مصروفات أخرى"]


def seed_expense_categories(db: DbSession) -> None:
    for name in DEFAULT_CATEGORIES:
        if not db.scalar(select(ExpenseCategory.id).where(ExpenseCategory.name == name)):
            db.add(ExpenseCategory(name=name))
    db.flush()


# ---- categories ---------------------------------------------------------------
class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)


@router.get("/expense-categories")
def list_categories(_: User = Depends(require("expenses.read")), db: DbSession = Depends(get_db, scope="function")):
    return [{"id": c.id, "name": c.name, "is_active": c.is_active}
            for c in db.scalars(select(ExpenseCategory).order_by(ExpenseCategory.id))]


@router.post("/expense-categories", status_code=201)
def create_category(body: CategoryIn, request: Request, user: User = Depends(require("expenses.write")),
                    db: DbSession = Depends(get_db, scope="function")):
    if db.scalar(select(ExpenseCategory.id).where(func.lower(ExpenseCategory.name) == body.name.lower())):
        raise AppError("التصنيف موجود بالفعل", 409, "duplicate_category")
    c = ExpenseCategory(name=body.name)
    db.add(c)
    db.flush()
    audit(db, user, "expense_category.create", "expense_category", c.id, after={"name": c.name}, ip=client_ip(request))
    return {"id": c.id, "name": c.name, "is_active": True}


# ---- expenses ---------------------------------------------------------------------
class ExpenseIn(BaseModel):
    category_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    expense_date: date
    description: str = Field(min_length=2)
    payee: str | None = None
    method: str | None = None
    reference: str | None = None


class VoidIn(BaseModel):
    reason: str = Field(min_length=3)


def exp_out(e: Expense, cat: str | None = None) -> dict:
    return {"id": e.id, "category_id": e.category_id, "category": cat, "amount": f"{Decimal(e.amount):.2f}",  # always 2 decimals (a request amount like 1e2 used to be echoed, and audited, as "1E+2")
            "expense_date": e.expense_date, "description": e.description, "payee": e.payee, "method": e.method,
            "reference": e.reference, "is_void": e.is_void, "void_reason": e.void_reason}


@router.post("/expenses", status_code=201)
def create_expense(body: ExpenseIn, request: Request, user: User = Depends(require("expenses.write")),
                   db: DbSession = Depends(get_db, scope="function")):
    cat = db.get(ExpenseCategory, body.category_id)
    if not cat or not cat.is_active:
        raise AppError("التصنيف غير موجود", 422, "bad_category")
    e = Expense(**body.model_dump(), created_by=user.id)
    db.add(e)
    db.flush()
    audit(db, user, "expense.create", "expense", e.id, after=exp_out(e, cat.name), ip=client_ip(request))
    return exp_out(e, cat.name)


@router.get("/expenses")
def list_expenses(date_from: date | None = None, date_to: date | None = None, category_id: int | None = None,
                  include_void: bool = False, limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
                  _: User = Depends(require("expenses.read")), db: DbSession = Depends(get_db, scope="function")):
    q = select(Expense, ExpenseCategory.name).join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
    if date_from:
        q = q.where(Expense.expense_date >= date_from)
    if date_to:
        q = q.where(Expense.expense_date <= date_to)
    if category_id:
        q = q.where(Expense.category_id == category_id)
    if not include_void:
        q = q.where(Expense.is_void.is_(False))
    matching = q.with_only_columns(Expense.id, Expense.amount, Expense.is_void).subquery()
    total = db.scalar(select(func.coalesce(func.sum(matching.c.amount), 0)).where(matching.c.is_void.is_(False)))
    count = db.scalar(select(func.count()).select_from(matching))
    rows = db.execute(q.order_by(Expense.expense_date.desc(), Expense.id.desc()).limit(limit).offset(offset)).all()
    return {"total": str(to_money(total)), "total_count": count,
            "items": [exp_out(e, n) for e, n in rows]}


@router.post("/expenses/{expense_id}/void")
def void_expense(expense_id: int, body: VoidIn, request: Request, user: User = Depends(require("expenses.write")),
                 db: DbSession = Depends(get_db, scope="function")):
    e = db.get(Expense, expense_id)
    if not e:
        raise AppError("المصروف غير موجود", 404, "not_found")
    if e.is_void:
        raise AppError("المصروف ملغي بالفعل", 409, "already_void")
    e.is_void, e.void_reason = True, body.reason
    audit(db, user, "expense.void", "expense", e.id, before={"amount": str(e.amount)}, reason=body.reason, ip=client_ip(request))
    return exp_out(e)


# ---- financial summary -------------------------------------------------------------
@router.get("/reports/financial-summary")
def financial_summary(date_from: date | None = None, date_to: date | None = None,
                      _: User = Depends(require("reports.financial")), db: DbSession = Depends(get_db, scope="function")):
    today = datetime.now(TZ).date()
    d_from = date_from or today.replace(day=1)
    d_to = date_to or today
    if d_to < d_from:
        raise AppError("تاريخ النهاية قبل البداية", 422, "bad_range")
    start = datetime.combine(d_from, time.min, TZ)
    end = next_day_start(d_to, TZ)

    invoices = list(db.scalars(select(Invoice).where(Invoice.status == "issued", Invoice.issued_at >= start,
                                                     Invoice.issued_at < end)))
    inv_ids = [i.id for i in invoices]
    revenue = sum((Decimal(i.subtotal) - Decimal(i.discount) for i in invoices), ZERO)
    tax = sum((Decimal(i.tax_amount) for i in invoices), ZERO)
    by_kind = {"labor": ZERO, "part": ZERO, "other": ZERO}      # as billed (before the invoice discount)
    net_by_kind = {"labor": ZERO, "part": ZERO, "other": ZERO}  # after spreading each invoice's discount over its categories
    parts_cost = ZERO
    cost_by_source = {"direct": ZERO, "warehouse": ZERO, "customer": ZERO}
    revenue_by_source = {"direct": ZERO, "warehouse": ZERO, "customer": ZERO}
    if inv_ids:
        per_invoice: dict = {}
        for inv_id, kind, amt in db.execute(select(InvoiceItem.invoice_id, InvoiceItem.kind, func.sum(InvoiceItem.amount))
                                            .where(InvoiceItem.invoice_id.in_(inv_ids)).group_by(InvoiceItem.invoice_id, InvoiceItem.kind)):
            per_invoice.setdefault(inv_id, {"labor": ZERO, "part": ZERO, "other": ZERO})[kind] = to_money(amt)
            by_kind[kind] += to_money(amt)
        for i in invoices:
            for kind, amt in allocate_discount(per_invoice.get(i.id, {"labor": ZERO, "part": ZERO, "other": ZERO}), Decimal(i.discount)).items():
                net_by_kind[kind] += amt
        for item, part in db.execute(select(InvoiceItem, PartPurchase).join(PartPurchase, PartPurchase.id == InvoiceItem.part_id)
                                     .where(InvoiceItem.invoice_id.in_(inv_ids))):
            line_cost = to_money(Decimal(item.quantity) * Decimal(part.unit_cost))
            parts_cost += line_cost
            cost_by_source[part.source] += line_cost
            revenue_by_source[part.source] += Decimal(item.amount)
    # billed units that went back to the supplier / the warehouse in this period take their cost out of COGS again
    returned_by_source = cogs_returned_in_period(db, start, end, by_source=True)
    parts_cost_returned = sum(returned_by_source.values(), ZERO)
    parts_cost_net = parts_cost - parts_cost_returned
    # credit notes issued in the period reduce revenue (net of the tax they contain)
    credit_ex_tax, credit_gross, tax_credited = ZERO, ZERO, ZERO
    for cn, inv_row in db.execute(select(CreditNote, Invoice).join(Invoice, Invoice.id == CreditNote.invoice_id)
                                  .where(CreditNote.created_at >= start, CreditNote.created_at < end)):
        credit_gross += Decimal(cn.amount)
        ex_tax = to_money(Decimal(cn.amount) / (1 + Decimal(inv_row.tax_rate) / 100))
        credit_ex_tax += ex_tax
        tax_credited += Decimal(cn.amount) - ex_tax
    cash_in = to_money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))
                                 .where(Payment.paid_at >= start, Payment.paid_at < end)))
    cash_out = to_money(db.scalar(select(func.coalesce(func.sum(Refund.amount), 0))
                                  .where(Refund.refunded_at >= start, Refund.refunded_at < end)))
    opex = to_money(db.scalar(select(func.coalesce(func.sum(Expense.amount), 0))
                              .where(Expense.is_void.is_(False), Expense.expense_date >= d_from, Expense.expense_date <= d_to)))
    issued = list(db.scalars(select(Invoice).where(Invoice.status == "issued")))
    receivables = sum((max(st["outstanding"], ZERO) for st in money_states(db, issued).values()), ZERO)  # 3 queries, not 3 per invoice
    net_revenue = revenue - credit_ex_tax
    gross = net_revenue - parts_cost_net
    # ---- inventory & purchasing (accrual vs cash kept apart; purchases and supplier payments are NEVER operating expenses) ----
    posted_purchases = to_money(db.scalar(select(func.coalesce(func.sum(PurchaseInvoice.subtotal - PurchaseInvoice.discount), 0))
                                          .where(PurchaseInvoice.status == "posted", PurchaseInvoice.posted_at >= start, PurchaseInvoice.posted_at < end)))
    received_value = to_money(db.scalar(select(func.coalesce(func.sum(StockMovement.value_delta), 0))
                                        .where(StockMovement.doc_type == "goods_receipt", StockMovement.movement_type.in_(("GOODS_RECEIPT", "REVERSAL")),
                                               StockMovement.ts >= start, StockMovement.ts < end)))
    supplier_paid = to_money(db.scalar(select(func.coalesce(func.sum(SupplierPayment.amount), 0)).where(SupplierPayment.paid_at >= start, SupplierPayment.paid_at < end)))
    supplier_owed = sum((r["outstanding"] for r in pur.supplier_balances(db)), ZERO)
    stock_value = to_money(db.scalar(select(func.coalesce(func.sum(InventoryBalance.value), 0))))
    s = lambda v: str(to_money(v))  # noqa: E731
    parts_manual = by_kind["part"] - sum(revenue_by_source.values(), ZERO)  # 'part' lines typed by hand (no linked part)
    return {"date_from": d_from, "date_to": d_to, "currency": cfg.get_section(db, "finance")["currency"], "invoices_issued": len(invoices),
            "basis": {"profit": "accrual: invoices issued in the period; parts cost is recognised when stock/direct parts are consumed by a billed job",
                      "cash": "payments received / paid in the period"},
            "parts_revenue_warehouse": s(revenue_by_source["warehouse"]), "parts_revenue_direct": s(revenue_by_source["direct"]),
            "parts_revenue_customer_supplied": s(revenue_by_source["customer"]), "parts_revenue_manual": s(parts_manual),
            "cogs_warehouse": s(cost_by_source["warehouse"] - returned_by_source["warehouse"]), "cogs_direct": s(cost_by_source["direct"] - returned_by_source["direct"]),
            "cogs_customer_supplied": s(cost_by_source["customer"] - returned_by_source["customer"]),
            "inventory_purchases": s(posted_purchases), "inventory_received_value": s(received_value), "inventory_asset_value": s(stock_value),
            "supplier_payments": s(supplier_paid), "supplier_outstanding": s(supplier_owed),
            "net_cash_flow": s(cash_in - cash_out - supplier_paid - opex),
            "revenue_invoiced_ex_tax": s(revenue), "labor_billed": s(by_kind["labor"]), "parts_billed": s(by_kind["part"]),
            "other_billed": s(by_kind["other"]), "discount_invoiced": s(sum((Decimal(i.discount) for i in invoices), ZERO)),
            "labor_net": s(net_by_kind["labor"]), "parts_net": s(net_by_kind["part"]), "other_net": s(net_by_kind["other"]),
            "tax_invoiced": s(tax), "tax_credited": s(tax_credited), "net_tax": s(tax - tax_credited), "credit_notes": s(credit_gross),
            "net_revenue_ex_tax": s(net_revenue), "cash_received": s(cash_in), "refunds_paid": s(cash_out),
            "net_cash_collected": s(cash_in - cash_out), "direct_costs_parts": s(parts_cost_net), "parts_cost_billed": s(parts_cost),
            "parts_cost_returned": s(parts_cost_returned), "gross_profit": s(gross),
            "operating_expenses": s(opex), "estimated_net_profit": s(gross - opex),
            "receivables_outstanding": s(receivables)}
