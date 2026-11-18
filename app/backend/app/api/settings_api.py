"""Application settings API."""
import re
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, current_user, require
from app.core.audit import audit
from app.core.errors import AppError
from app.db import get_db
from app.models import AppSetting
from app.models.auth import User
from app.services import settings as svc

router = APIRouter(prefix="/api", tags=["settings"])


class Workshop(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    name_en: str = Field("", max_length=200)
    address: str = Field("", max_length=500)
    phone: str = Field("", max_length=60)
    email: str = Field("", max_length=200)
    tax_number: str = Field("", max_length=60)


class PayMethod(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]{2,30}$")
    label: str = Field(min_length=1, max_length=50)


class LaborRate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    rate: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class Finance(BaseModel):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    default_tax_rate: Decimal = Field(Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)
    invoice_prefix: str = Field(pattern=r"^[A-Za-z0-9\-]{1,10}$")
    credit_prefix: str = Field(pattern=r"^[A-Za-z0-9\-]{1,10}$")
    job_prefix: str = Field(pattern=r"^[A-Za-z0-9\-]{0,10}$")
    number_width: int = Field(ge=1, le=10)
    payment_methods: list[PayMethod] = Field(min_length=1)
    default_labor_rate: Decimal = Field(Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    labor_rates: list[LaborRate] = []

    @field_validator("payment_methods")
    @classmethod
    def unique_keys(cls, v):
        keys = [m.key for m in v]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate payment method")
        return v


class Hours(BaseModel):
    open: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    close: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    days: list[int]


class General(BaseModel):
    language: str = Field("en", pattern="^(ar|en)$")  # default UI language for devices that have not chosen one
    theme: str = Field(pattern="^(light|dark)$")
    working_hours: Hours


class Warranty(BaseModel):
    default_part_months: int = Field(ge=0, le=240)
    default_labor_months: int = Field(ge=0, le=240)


class Security(BaseModel):
    session_minutes: int = Field(ge=5, le=1440)
    max_failed_logins: int = Field(ge=3, le=20)
    lockout_minutes: int = Field(ge=1, le=1440)


class RepairCatalogItem(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    category: str
    name: str = Field(min_length=1, max_length=200)
    initial_price: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def known_category(cls, value):
        from app.services.templates import REPAIR_TEMPLATES
        if value not in REPAIR_TEMPLATES:
            raise ValueError("unknown repair category")
        return value


class RepairCatalog(BaseModel):
    items: list[RepairCatalogItem] = Field(max_length=500)

    @field_validator("items")
    @classmethod
    def unique_items(cls, items):
        if len({x.id for x in items}) != len(items):
            raise ValueError("duplicate id")
        if len({(x.category, x.name.casefold()) for x in items}) != len(items):
            raise ValueError("duplicate name in category")
        return items


MODELS = {"repair_catalog": RepairCatalog, "workshop": Workshop, "finance": Finance, "general": General, "warranty": Warranty, "security": Security}
SECTION_PERMISSION = {"security": "users.manage"}  # everything else needs settings.manage


def _json(model: BaseModel) -> dict:
    return model.model_dump(mode="json")


@router.get("/settings")
def get_all(_: User = Depends(current_user), db: DbSession = Depends(get_db, scope="function")):
    """Everything the UI needs to render (names, currency, methods, prefixes). Security settings are admin-only."""
    out = {k: svc.get_section(db, k) for k in MODELS if k != "security"}
    out["demo"] = db.get(AppSetting, "demo") is not None  # set by the sample-data generator
    return out


@router.get("/settings/security")
def get_security(_: User = Depends(require("users.manage")), db: DbSession = Depends(get_db, scope="function")):
    return svc.get_section(db, "security")


@router.put("/settings/{section}")
def put_section(section: str, body: dict, request: Request, user: User = Depends(current_user),
                db: DbSession = Depends(get_db, scope="function")):
    if section not in MODELS:
        raise AppError("قسم إعدادات غير معروف", 404, "not_found")
    need = SECTION_PERMISSION.get(section, "settings.manage")
    if need not in user.permissions:
        raise AppError("ليس لديك صلاحية لهذا الإجراء", 403, "forbidden")
    try:
        clean = _json(MODELS[section].model_validate(body))
    except Exception as e:  # noqa: BLE001 - pydantic ValidationError
        raise AppError("تأكد من القيم المدخلة في الإعدادات", 422, "bad_settings") from e
    before = svc.get_section(db, section)
    svc.set_section(db, section, clean)
    audit(db, user, "settings.update", "settings", section, before=before, after=clean, ip=client_ip(request))
    return clean


def format_number(db: DbSession, kind: str, n: int) -> str:
    f = svc.get_section(db, "finance")
    prefix = f["invoice_prefix"] if kind == "invoice" else f["credit_prefix"]
    return f"{prefix}-{n:0{int(f['number_width'])}d}"


_ = re  # (kept for validators above)
