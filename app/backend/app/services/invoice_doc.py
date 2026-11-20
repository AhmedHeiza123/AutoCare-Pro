"""The ONE customer-facing invoice calculation. Both print layouts (detailed / summary), the on-screen preview and the PDF are
produced from this single dictionary, which in turn is built only from the stored invoice records.

Customer-confidential data (purchase cost, margin, internal labor cost, profit, internal notes) is never read here: the
queries below select only selling-side columns, and `FORBIDDEN_KEYS` is asserted on the finished document.

Nothing in this module writes to the database."""
import hashlib
import hmac
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.en_text import EN
from app.core.money import to_money
from app.models import (Attachment, CreditNote, Customer, Invoice, InvoiceItem, PartPurchase, Payment, RepairOperation,
                        Refund, Vehicle, VehicleVisit)
from app.services import settings as cfg

MODES = ("detailed", "summary")
FORBIDDEN_KEYS = {"unit_cost", "cost", "purchase_cost", "profit", "margin", "labor_cost", "supplier", "supplier_id", "notes", "internal_notes"}
ZERO = Decimal("0.00")
STD_METHODS_EN = {"cash": "Cash", "bank_transfer": "Bank transfer", "card": "Card", "cheque": "Cheque", "other": "Other"}

LABELS = {
    "ar": {
        "title": "فاتورة", "invoice_no": "رقم الفاتورة", "date": "التاريخ", "job": "أمر الصيانة", "customer": "العميل", "mobile": "الجوال",
        "vehicle": "السيارة", "plate": "رقم اللوحة", "vin": "رقم الشاسيه", "mileage": "العداد", "km": "كم", "completed": "تاريخ الإنجاز",
        "delivered": "تاريخ التسليم", "desc": "البيان", "part_no": "رقم القطعة", "qty": "الكمية", "unit": "سعر الوحدة", "total": "الإجمالي",
        "hours": "ساعات", "rate": "سعر الساعة", "parts": "قطع الغيار", "labor": "الأجور", "other": "رسوم إضافية", "discount": "الخصم",
        "tax": "الضريبة", "subtotal": "المجموع قبل الخصم", "grand_total": "إجمالي الفاتورة", "paid": "المدفوع", "refunded": "المسترد",
        "credit": "إشعارات دائنة", "outstanding": "المتبقي", "payments": "الدفعات", "method": "طريقة الدفع", "page": "صفحة", "of": "من",
        "draft": "مسودة", "cancelled": "ملغاة", "tax_no": "الرقم الضريبي", "thanks": "شكراً لتعاملكم معنا", "summary_note": "فاتورة مختصرة",
        "detailed_note": "فاتورة تفصيلية", "ref": "مرجع", "paid_in_full": "مسددة بالكامل",
    },
    "en": {
        "title": "Invoice", "invoice_no": "Invoice no.", "date": "Date", "job": "Job card", "customer": "Customer", "mobile": "Mobile",
        "vehicle": "Vehicle", "plate": "Plate", "vin": "VIN", "mileage": "Mileage", "km": "km", "completed": "Completed",
        "delivered": "Delivered", "desc": "Description", "part_no": "Part no.", "qty": "Qty", "unit": "Unit price", "total": "Total",
        "hours": "hrs", "rate": "Rate", "parts": "Spare parts", "labor": "Labor", "other": "Additional charges", "discount": "Discount",
        "tax": "Tax", "subtotal": "Subtotal", "grand_total": "Invoice total", "paid": "Amount paid", "refunded": "Refunded",
        "credit": "Credit notes", "outstanding": "Outstanding balance", "payments": "Payments", "method": "Method", "page": "Page", "of": "of",
        "draft": "DRAFT", "cancelled": "CANCELLED", "tax_no": "Tax no.", "thanks": "Thank you for your business", "summary_note": "Summary invoice",
        "detailed_note": "Detailed invoice", "ref": "Ref", "paid_in_full": "Paid in full",
    },
}


def money(v) -> str:
    return f"{Decimal(str(v)):.2f}"


def qr_signature(inv: Invoice) -> str:
    msg = f"{inv.id}|{inv.invoice_no}|{Decimal(inv.total):.2f}".encode()
    return hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()[:20]


def qr_token(inv: Invoice) -> str:
    return f"AC1:{inv.invoice_no}:{Decimal(inv.total):.2f}:{qr_signature(inv)}"


def verify_token(db: Session, token: str) -> dict:
    """Checks a scanned QR token against the stored invoice (authenticated by an HMAC only this installation can make)."""
    parts = token.strip().split(":")
    if len(parts) != 4 or parts[0] != "AC1" or not parts[1].isdigit():
        return {"valid": False, "reason": "malformed"}
    inv = db.scalar(select(Invoice).where(Invoice.invoice_no == int(parts[1])))
    if not inv or not hmac.compare_digest(parts[3], qr_signature(inv)) or parts[2] != f"{Decimal(inv.total):.2f}":
        return {"valid": False, "reason": "mismatch"}
    return {"valid": True, "number": cfg_number(db, inv), "total": money(inv.total), "status": inv.status, "invoice_id": str(inv.id)}


def cfg_number(db: Session, inv: Invoice) -> str:
    f = cfg.get_section(db, "finance")
    return f"{f['invoice_prefix']}-{inv.invoice_no:0{int(f['number_width'])}d}"


def _t(text: str | None, lang: str, extra: dict | None = None) -> str:
    """English text for an Arabic one: names the workshop typed in the repair catalog win over the built-in dictionary."""
    text = text or ""
    if lang != "en":
        return text
    return (extra or {}).get(text) or EN.get(text, text)


def logo_path(db: Session):
    a = db.scalar(select(Attachment).where(Attachment.owner_type == "workshop", Attachment.owner_id == "logo",
                                           Attachment.is_removed.is_(False)).order_by(Attachment.uploaded_at.desc()))
    if not a or not str(a.mime).startswith("image/"):
        return None
    p = get_settings().storage_dir / "attachments" / a.stored_path
    return p if p.is_file() else None


def build_document(db: Session, inv: Invoice, mode: str = "detailed", lang: str = "ar", with_qr: bool = True) -> dict:
    if mode not in MODES:
        raise ValueError("mode")
    if lang not in ("ar", "en"):
        raise ValueError("lang")
    from app.api.billing import money_state  # local import: billing imports nothing from here

    snap = inv.doc_snapshot or {}
    ws = snap.get("workshop") or cfg.get_section(db, "workshop")
    methods = snap.get("payment_methods") or {m["key"]: m["label"] for m in cfg.get_section(db, "finance")["payment_methods"]}
    currency = snap.get("currency") or inv.currency
    st = money_state(db, inv)
    cust = db.get(Customer, inv.customer_id)
    veh = db.get(Vehicle, inv.vehicle_id)
    job = db.get(VehicleVisit, inv.visit_id)

    parts_total = labor_total = other_total = ZERO
    catalog_names = cfg.catalog_en(db) if lang == "en" else {}
    lines = []
    for it in db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id).order_by(InvoiceItem.id)):
        amount = to_money(it.amount)
        line = {"kind": it.kind, "description": _t(it.description, lang, catalog_names), "quantity": money(it.quantity),
                "unit_price": money(it.unit_price), "amount": money(amount), "part_number": None, "hours": None, "rate": None}
        if it.kind == "part":
            parts_total += amount
            pp = db.get(PartPurchase, it.part_id) if it.part_id else None
            line["part_number"] = pp.part_number if pp else None  # customer-facing identifier only; never cost/supplier
        elif it.kind == "labor":
            labor_total += amount
            op = db.get(RepairOperation, it.operation_id) if it.operation_id else None
            if op and to_money(Decimal(op.labor_hours) * Decimal(op.labor_rate)) == amount and Decimal(op.labor_hours) > 0:
                line.update(hours=money(op.labor_hours), rate=money(op.labor_rate), quantity=money(op.labor_hours), unit_price=money(op.labor_rate))
        else:
            other_total += amount
        lines.append(line)

    pays = []
    for p in db.scalars(select(Payment).where(Payment.invoice_id == inv.id).order_by(Payment.id)):
        label = methods.get(p.method, p.method)
        if lang == "en":
            label = STD_METHODS_EN.get(p.method, _t(label, lang))
        pays.append({"date": p.paid_at.date().isoformat() if p.paid_at else None, "method": label, "amount": money(p.amount), "kind": p.kind})
    refunds = sum((Decimal(r.amount) for r in db.scalars(select(Refund).join(Payment, Payment.id == Refund.payment_id).where(Payment.invoice_id == inv.id))), ZERO)

    doc = {
        "mode": mode, "lang": lang, "rtl": lang == "ar",
        "invoice": {"id": str(inv.id), "number": cfg_number(db, inv), "date": (inv.invoice_date or (inv.issued_at.date() if inv.issued_at else None)).isoformat()
                    if (inv.invoice_date or inv.issued_at) else None, "status": inv.status, "currency": currency, "job_no": job.visit_no},
        "workshop": {"name": (ws.get("name_en") if lang == "en" and ws.get("name_en") else ws.get("name")), "address": ws.get("address", ""),
                     "phone": ws.get("phone", ""), "email": ws.get("email", ""), "tax_number": ws.get("tax_number", ""), "has_logo": logo_path(db) is not None},
        "customer": {"name": cust.full_name, "mobile": cust.mobile},
        "vehicle": {"make": veh.make, "model": veh.model, "plate": veh.plate, "vin": veh.vin, "mileage": job.mileage},
        "visit": {"completed_at": job.completed_at.date().isoformat() if job.completed_at else None,
                  "delivered_at": job.delivered_at.date().isoformat() if job.delivered_at else None},
        "groups": {"parts": money(parts_total), "labor": money(labor_total), "other": money(other_total)},
        "totals": {"subtotal": money(inv.subtotal), "discount": money(inv.discount), "tax_rate": money(inv.tax_rate), "tax_amount": money(inv.tax_amount),
                   "total": money(inv.total), "credit_total": money(st["credit_total"]), "paid": money(st["paid"]), "refunded": money(refunds),
                   "net_paid": money(st["net_paid"]), "due": money(st["due"]), "outstanding": money(st["outstanding"]),
                   "payment_status": st["payment_status"]},
        "payments": pays,
        "labels": LABELS[lang],
        "qr": qr_token(inv) if with_qr and inv.status != "draft" else None,
    }
    if mode == "detailed":
        doc["lines"] = lines
    # summary mode: individual charges are simply never put into the document
    _assert_confidential(doc)
    return doc


def _assert_confidential(node) -> None:
    if isinstance(node, dict):
        bad = FORBIDDEN_KEYS & {str(k).lower() for k in node}
        if bad:
            raise RuntimeError(f"customer document would expose {sorted(bad)}")
        for v in node.values():
            _assert_confidential(v)
    elif isinstance(node, list):
        for v in node:
            _assert_confidential(v)
