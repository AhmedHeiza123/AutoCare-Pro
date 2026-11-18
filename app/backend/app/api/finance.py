"""Operating expenses (void, never delete) and the financial summary report."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.billing import ZERO, money_state
from app.api.deps import client_ip, require
from app.core.audit import audit
from app.services import settings as cfg
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (CreditNote, Expense, ExpenseCategory, Invoice, InvoiceItem, PartPurchase, Payment,
                        Refund)
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
    return {"id": e.id, "category_id": e.category_id, "category": cat, "amount": str(e.amount),
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
    end = datetime.combine(d_to + timedelta(days=1), time.min, TZ)

    invoices = list(db.scalars(select(Invoice).where(Invoice.status == "issued", Invoice.issued_at >= start,
                                                     Invoice.issued_at < end)))
    inv_ids = [i.id for i in invoices]
    revenue = sum((Decimal(i.subtotal) - Decimal(i.discount) for i in invoices), ZERO)
    tax = sum((Decimal(i.tax_amount) for i in invoices), ZERO)
    by_kind = {"labor": ZERO, "part": ZERO, "other": ZERO}
    parts_cost = ZERO
    if inv_ids:
        for kind, amt in db.execute(select(InvoiceItem.kind, func.sum(InvoiceItem.amount))
                                    .where(InvoiceItem.invoice_id.in_(inv_ids)).group_by(InvoiceItem.kind)):
            by_kind[kind] = to_money(amt)
        for item, part in db.execute(select(InvoiceItem, PartPurchase).join(PartPurchase, PartPurchase.id == InvoiceItem.part_id)
                                     .where(InvoiceItem.invoice_id.in_(inv_ids))):
            parts_cost += to_money(Decimal(item.quantity) * Decimal(part.unit_cost))
    # credit notes issued in the period reduce revenue (net of the tax they contain)
    credit_ex_tax, credit_gross = ZERO, ZERO
    for cn, inv in db.execute(select(CreditNote, Invoice).join(Invoice, Invoice.id == CreditNote.invoice_id)
                              .where(CreditNote.created_at >= start, CreditNote.created_at < end)):
        credit_gross += Decimal(cn.amount)
        credit_ex_tax += to_money(Decimal(cn.amount) / (1 + Decimal(inv.tax_rate) / 100))
    cash_in = to_money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))
                                 .where(Payment.paid_at >= start, Payment.paid_at < end)))
    cash_out = to_money(db.scalar(select(func.coalesce(func.sum(Refund.amount), 0))
                                  .where(Refund.refunded_at >= start, Refund.refunded_at < end)))
    opex = to_money(db.scalar(select(func.coalesce(func.sum(Expense.amount), 0))
                              .where(Expense.is_void.is_(False), Expense.expense_date >= d_from, Expense.expense_date <= d_to)))
    receivables = sum((max(money_state(db, i)["outstanding"], ZERO)
                       for i in db.scalars(select(Invoice).where(Invoice.status == "issued"))), ZERO)
    net_revenue = revenue - credit_ex_tax
    gross = net_revenue - parts_cost
    s = lambda v: str(to_money(v))  # noqa: E731
    return {"date_from": d_from, "date_to": d_to, "currency": cfg.get_section(db, "finance")["currency"], "invoices_issued": len(invoices),
            "revenue_invoiced_ex_tax": s(revenue), "labor_billed": s(by_kind["labor"]), "parts_billed": s(by_kind["part"]),
            "other_billed": s(by_kind["other"]), "tax_invoiced": s(tax), "credit_notes": s(credit_gross),
            "net_revenue_ex_tax": s(net_revenue), "cash_received": s(cash_in), "refunds_paid": s(cash_out),
            "net_cash_collected": s(cash_in - cash_out), "direct_costs_parts": s(parts_cost), "gross_profit": s(gross),
            "operating_expenses": s(opex), "estimated_net_profit": s(gross - opex),
            "receivables_outstanding": s(receivables)}
