from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.core.audit import audit, snapshot
from app.core.errors import AppError
from app.core.text import digits, normalize
from app.db import get_db
from app.models import Customer, Vehicle
from app.models.auth import User

router = APIRouter(prefix="/api/customers", tags=["customers"])

FIELDS = ["customer_type", "full_name", "company_name", "mobile", "alt_phone", "email", "address",
          "city", "country", "tax_number", "notes", "is_active"]


class CustomerIn(BaseModel):
    customer_type: str = Field("individual", pattern="^(individual|company)$")
    full_name: str = Field(min_length=2, max_length=200)
    company_name: str | None = None
    mobile: str = Field(min_length=5, max_length=40)
    alt_phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    tax_number: str | None = None
    notes: str | None = None


class CustomerPatch(BaseModel):
    customer_type: str | None = Field(None, pattern="^(individual|company)$")
    full_name: str | None = Field(None, min_length=2, max_length=200)
    company_name: str | None = None
    mobile: str | None = Field(None, min_length=5, max_length=40)
    alt_phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    tax_number: str | None = None
    notes: str | None = None
    is_active: bool | None = None


def out(c: Customer) -> dict:
    d = {f: getattr(c, f) for f in FIELDS}
    d.update(id=str(c.id), customer_no=c.customer_no, created_at=c.created_at)
    return d


def _reindex(c: Customer) -> None:
    c.mobile_compact = digits(c.mobile)
    c.search_text = normalize(" ".join(filter(None, [
        c.full_name, c.company_name, c.mobile, c.alt_phone, c.email, str(c.customer_no or "")])))


def find_duplicates(db: DbSession, mobile: str, full_name: str, exclude: UUID | None = None):
    # Names are compared in normalized form (alef/yaa/taa-marbuta unified, diacritics removed), exactly as search_text is built;
    # comparing the raw stored name with a normalized one missed duplicates of any name containing those letters.
    nm, dm = normalize(full_name), digits(mobile)
    conds = [Customer.search_text.contains(nm)] if nm else []
    if dm:
        conds.append(Customer.mobile_compact == dm)
    if not conds:
        return []
    q = select(Customer).where(or_(*conds))
    if exclude:
        q = q.where(Customer.id != exclude)
    found = [c for c in db.scalars(q.limit(200)) if (dm and c.mobile_compact == dm) or normalize(c.full_name) == nm]
    return found[:5]


@router.post("", status_code=201)
def create_customer(body: CustomerIn, request: Request, force: bool = False,
                    user: User = Depends(require("customers.write")), db: DbSession = Depends(get_db, scope="function")):
    if not force:
        dups = find_duplicates(db, body.mobile, body.full_name)
        if dups:
            from fastapi.responses import JSONResponse
            from fastapi.encoders import jsonable_encoder
            return JSONResponse(status_code=409, content={
                "error": "possible_duplicate", "message": "يوجد عميل مشابه، هل تريد المتابعة؟",
                "duplicates": jsonable_encoder([out(d) for d in dups])})
    c = Customer(**body.model_dump())
    _reindex(c)  # mobile_compact is NOT NULL, so index before the first INSERT
    db.add(c)
    db.flush()  # customer_no assigned here; reindex again so the number is searchable
    _reindex(c)
    audit(db, user, "customer.create", "customer", c.id, after=snapshot(c, FIELDS), ip=client_ip(request))
    return out(c)


@router.get("")
def list_customers(q: str | None = None, active: bool | None = None, limit: int = Query(50, le=200),
                   offset: int = 0, _: User = Depends(require("customers.read")),
                   db: DbSession = Depends(get_db, scope="function")):
    stmt = select(Customer)
    if q:
        conds = [Customer.search_text.contains(normalize(q))]
        if digits(q):  # an empty digit string would match every row
            conds.append(Customer.mobile_compact.contains(digits(q)))
        stmt = stmt.where(or_(*conds))
    if active is not None:
        stmt = stmt.where(Customer.is_active == active)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Customer.full_name).limit(limit).offset(offset))
    return {"total": total, "items": [out(c) for c in rows]}


@router.get("/{customer_id}")
def get_customer(customer_id: UUID, _: User = Depends(require("customers.read")),
                 db: DbSession = Depends(get_db, scope="function")):
    c = db.get(Customer, customer_id)
    if not c:
        raise AppError("العميل غير موجود", 404, "not_found")
    vehicles = db.scalars(select(Vehicle).where(Vehicle.current_customer_id == c.id))
    d = out(c)
    d["vehicles"] = [{"id": str(v.id), "make": v.make, "model": v.model, "plate": v.plate}
                     for v in vehicles]
    return d


@router.patch("/{customer_id}")
def update_customer(customer_id: UUID, body: CustomerPatch, request: Request,
                    user: User = Depends(require("customers.write")), db: DbSession = Depends(get_db, scope="function")):
    c = db.get(Customer, customer_id)
    if not c:
        raise AppError("العميل غير موجود", 404, "not_found")
    before = snapshot(c, FIELDS)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    _reindex(c)
    audit(db, user, "customer.update", "customer", c.id, before=before, after=snapshot(c, FIELDS),
          ip=client_ip(request))
    return out(c)
