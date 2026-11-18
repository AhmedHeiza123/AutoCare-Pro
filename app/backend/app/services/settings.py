"""Business settings stored in the database (editable from the UI; no config files needed)."""
from copy import deepcopy
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import AppSetting
from app.services.templates import REPAIR_TEMPLATES

DEFAULTS: dict[str, dict] = {
    "repair_catalog": {"items": [{"id": f"{category}-{i+1}", "category": category, "name": name, "initial_price": None, "active": True} for category, names in REPAIR_TEMPLATES.items() for i, name in enumerate(names)]},
    "workshop": {"name": "ورشة السيارات", "name_en": "", "address": "", "phone": "", "email": "", "tax_number": ""},
    "finance": {
        "currency": "QAR", "default_tax_rate": "0", "invoice_prefix": "INV", "credit_prefix": "CN", "job_prefix": "JOB",
        "number_width": 6,
        "payment_methods": [{"key": "cash", "label": "كاش"}, {"key": "bank_transfer", "label": "تحويل بنكي"},
                            {"key": "card", "label": "كارت"}, {"key": "cheque", "label": "شيك"}, {"key": "other", "label": "أخرى"}],
        "default_labor_rate": "0", "labor_rates": [],
    },
    "general": {"language": "en", "theme": "light", "working_hours": {"open": "08:00", "close": "18:00", "days": [0, 1, 2, 3, 4, 5]}},
    "warranty": {"default_part_months": 0, "default_labor_months": 0},
    "security": {"session_minutes": 480, "max_failed_logins": 5, "lockout_minutes": 15},
}


def get_section(db: Session, section: str) -> dict:
    merged = deepcopy(DEFAULTS[section])
    row = db.get(AppSetting, f"cfg.{section}")
    if row:
        merged.update(row.value)
    if section == "finance":  # canonical 2-decimal money strings
        for k in ("default_tax_rate", "default_labor_rate"):
            merged[k] = f"{Decimal(str(merged[k])):.2f}"
        merged["labor_rates"] = [{**r, "rate": f"{Decimal(str(r['rate'])):.2f}"} for r in merged["labor_rates"]]
    if section == "repair_catalog":
        for item in merged["items"]:
            if item.get("initial_price") is not None:
                item["initial_price"] = f"{Decimal(str(item['initial_price'])):.2f}"
    return merged


def set_section(db: Session, section: str, value: dict) -> None:
    row = db.get(AppSetting, f"cfg.{section}")
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=f"cfg.{section}", value=value))
    db.flush()


def payment_method_keys(db: Session) -> list[str]:
    return [m["key"] for m in get_section(db, "finance")["payment_methods"]]
