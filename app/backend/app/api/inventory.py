"""Inventory & purchasing API: catalog, warehouses, balances, the stock ledger, purchase invoices, goods receipts, supplier payments,
adjustments, counts, transfers and the inventory dashboard. Business rules live in app.services.inventory / purchasing."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import client_ip, require
from app.core.audit import audit, snapshot
from app.core.dates import next_day_start
from app.core.errors import AppError
from app.core.money import to_money
from app.db import get_db
from app.models import (GoodsReceipt, GoodsReceiptLine, InventoryBalance, InventoryCategory, InventoryItem, PurchaseInvoice, PurchaseInvoiceLine,
                        StockAdjustment, StockAdjustmentLine, StockMovement, StockReservation, Supplier, SupplierCredit, SupplierPayment, Warehouse)
from app.models.auth import User
from app.services import inventory as inv
from app.services import purchasing as pur
from app.services import settings as cfg

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
TZ = ZoneInfo("Asia/Qatar")
ZERO = Decimal("0")
READ, WRITE, ADJUST, COSTS = require("inventory.read"), require("inventory.write"), require("inventory.adjust"), require("inventory.costs")
PUR_READ, PUR_WRITE = require("purchasing.read"), require("purchasing.write")
IDEM = Header(None, alias="Idempotency-Key", max_length=100)


def _costs(user: User) -> bool:
    return "inventory.costs" in user.permissions


def _num(x) -> str:
    return f"{Decimal(x):f}" if x is not None else None


# ---- categories & warehouses ------------------------------------------------------------------------------------------------
class CategoryIn(BaseModel):
    name_en: str = Field(min_length=1, max_length=120)
    name_ar: str = Field(min_length=1, max_length=120)
    parent_id: int | None = None


class CategoryPatch(BaseModel):
    name_en: str | None = Field(None, min_length=1, max_length=120)
    name_ar: str | None = Field(None, min_length=1, max_length=120)
    is_active: bool | None = None


def cat_out(c: InventoryCategory) -> dict:
    return {"id": c.id, "parent_id": c.parent_id, "name_en": c.name_en, "name_ar": c.name_ar, "is_active": c.is_active}


@router.get("/categories")
def list_categories(_: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    return [cat_out(c) for c in db.scalars(select(InventoryCategory).order_by(InventoryCategory.parent_id.nulls_first(), InventoryCategory.name_en))]


@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, request: Request, user: User = Depends(WRITE), db: DbSession = Depends(get_db, scope="function")):
    if body.parent_id is not None:
        parent = db.get(InventoryCategory, body.parent_id)
        if not parent or parent.parent_id is not None:
            raise AppError("التصنيف الأب غير موجود أو هو نفسه تصنيف فرعي", 422, "bad_parent")
    dup = select(InventoryCategory.id).where(func.coalesce(InventoryCategory.parent_id, 0) == (body.parent_id or 0),
                                             func.lower(InventoryCategory.name_en) == body.name_en.strip().lower())
    if db.scalar(dup):
        raise AppError("التصنيف موجود بالفعل", 409, "duplicate_category")
    c = InventoryCategory(name_en=body.name_en.strip(), name_ar=body.name_ar.strip(), parent_id=body.parent_id)
    db.add(c)
    db.flush()
    audit(db, user, "inventory.category.create", "inventory_category", c.id, after=cat_out(c), ip=client_ip(request))
    return cat_out(c)


@router.patch("/categories/{cid}")
def update_category(cid: int, body: CategoryPatch, request: Request, user: User = Depends(WRITE), db: DbSession = Depends(get_db, scope="function")):
    c = db.get(InventoryCategory, cid)
    if not c:
        raise AppError("التصنيف غير موجود", 404, "not_found")
    before = cat_out(c)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(c, k, v.strip() if isinstance(v, str) else v)
    audit(db, user, "inventory.category.update", "inventory_category", c.id, before=before, after=cat_out(c), ip=client_ip(request))
    return cat_out(c)


class WarehouseIn(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{2,20}$")
    name_en: str = Field(min_length=1, max_length=120)
    name_ar: str = Field(min_length=1, max_length=120)


def wh_out(w: Warehouse) -> dict:
    return {"id": w.id, "code": w.code, "name_en": w.name_en, "name_ar": w.name_ar, "is_default": w.is_default, "is_active": w.is_active}


@router.get("/warehouses")
def list_warehouses(_: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    return [wh_out(w) for w in db.scalars(select(Warehouse).order_by(Warehouse.id))]


@router.post("/warehouses", status_code=201)
def create_warehouse(body: WarehouseIn, request: Request, user: User = Depends(ADJUST), db: DbSession = Depends(get_db, scope="function")):
    if db.scalar(select(Warehouse.id).where(func.upper(Warehouse.code) == body.code.upper())):
        raise AppError("كود المخزن مستخدم", 409, "duplicate_code")
    w = Warehouse(code=body.code.upper(), name_en=body.name_en, name_ar=body.name_ar, is_default=False)
    db.add(w)
    db.flush()
    audit(db, user, "inventory.warehouse.create", "warehouse", w.id, after=wh_out(w), ip=client_ip(request))
    return wh_out(w)


# ---- items --------------------------------------------------------------------------------------------------------------------
class ItemIn(BaseModel):
    sku: str = Field(min_length=2, max_length=60, pattern=r"^[A-Za-z0-9._/\- ]+$")
    name_en: str = Field(min_length=2, max_length=200)
    name_ar: str | None = Field(None, max_length=200)
    category_id: int | None = None
    subcategory_id: int | None = None
    brand: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=100)
    mfr_part_no: str | None = Field(None, max_length=100)
    oem_part_no: str | None = Field(None, max_length=100)
    barcode: str | None = Field(None, max_length=64)
    uom: str = Field("pcs", max_length=20)
    default_supplier_id: int | None = None
    purchase_price: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    selling_price: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    min_stock: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=3)
    reorder_qty: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=3)
    storage_location: str | None = Field(None, max_length=100)
    compatibility: list[str] | None = None
    notes: str | None = None


class ItemPatch(BaseModel):
    name_en: str | None = Field(None, min_length=2, max_length=200)
    name_ar: str | None = Field(None, max_length=200)
    category_id: int | None = None
    subcategory_id: int | None = None
    brand: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=100)
    mfr_part_no: str | None = Field(None, max_length=100)
    oem_part_no: str | None = Field(None, max_length=100)
    barcode: str | None = Field(None, max_length=64)
    uom: str | None = Field(None, max_length=20)
    default_supplier_id: int | None = None
    purchase_price: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=4)
    selling_price: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    min_stock: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=3)
    reorder_qty: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=3)
    storage_location: str | None = Field(None, max_length=100)
    compatibility: list[str] | None = None
    notes: str | None = None
    is_active: bool | None = None


ITEM_FIELDS = ["sku", "name_en", "name_ar", "category_id", "subcategory_id", "brand", "manufacturer", "mfr_part_no", "oem_part_no", "barcode", "uom",
               "default_supplier_id", "purchase_price", "selling_price", "min_stock", "reorder_qty", "storage_location", "compatibility", "notes", "is_active"]


def _clean(data: dict) -> dict:
    return {k: (v.strip() or None if isinstance(v, str) and k not in ("uom",) else v) for k, v in data.items()}


def _validate_item(db: DbSession, data: dict, exclude_id: int | None = None) -> None:
    cat, sub = data.get("category_id"), data.get("subcategory_id")
    if cat is not None and not db.get(InventoryCategory, cat):
        raise AppError("التصنيف غير موجود", 422, "bad_category")
    if sub is not None:
        s = db.get(InventoryCategory, sub)
        if not s or s.parent_id is None or (cat is not None and s.parent_id != cat):
            raise AppError("التصنيف الفرعي غير صحيح أو لا يتبع التصنيف المحدد", 422, "bad_subcategory")
    if data.get("default_supplier_id") is not None and not db.get(Supplier, data["default_supplier_id"]):
        raise AppError("المورد غير موجود", 422, "bad_supplier")
    if data.get("barcode"):
        q = select(InventoryItem.id).where(InventoryItem.barcode == data["barcode"])
        if exclude_id:
            q = q.where(InventoryItem.id != exclude_id)
        if db.scalar(q):
            raise AppError("الباركود مستخدم لصنف آخر", 409, "duplicate_barcode")
    if data.get("mfr_part_no"):
        q = select(InventoryItem.id).where(func.lower(InventoryItem.mfr_part_no) == data["mfr_part_no"].lower(),
                                           func.coalesce(func.lower(InventoryItem.brand), "") == (data.get("brand") or "").lower())
        if exclude_id:
            q = q.where(InventoryItem.id != exclude_id)
        if db.scalar(q):
            raise AppError("هذه القطعة (نفس الماركة ورقم المصنّع) مسجلة من قبل", 409, "duplicate_part")


def _balances(db: DbSession, item_ids: list[int], warehouse_id: int | None = None) -> dict[int, dict]:
    if not item_ids:
        return {}
    q = select(InventoryBalance.item_id, func.coalesce(func.sum(InventoryBalance.on_hand), 0), func.coalesce(func.sum(InventoryBalance.reserved), 0),
               func.coalesce(func.sum(InventoryBalance.value), 0)).where(InventoryBalance.item_id.in_(item_ids)).group_by(InventoryBalance.item_id)
    if warehouse_id is not None:
        q = q.where(InventoryBalance.warehouse_id == warehouse_id)
    return {i: {"on_hand": Decimal(o), "reserved": Decimal(r), "value": Decimal(v)} for i, o, r, v in db.execute(q)}


def item_out(item: InventoryItem, bal: dict | None, user: User, cats: dict | None = None) -> dict:
    bal = bal or {"on_hand": ZERO, "reserved": ZERO, "value": ZERO}
    available = bal["on_hand"] - bal["reserved"]
    d = {"id": item.id, "sku": item.sku, "name_en": item.name_en, "name_ar": item.name_ar, "category_id": item.category_id,
         "subcategory_id": item.subcategory_id, "brand": item.brand, "manufacturer": item.manufacturer, "mfr_part_no": item.mfr_part_no,
         "oem_part_no": item.oem_part_no, "barcode": item.barcode, "uom": item.uom, "default_supplier_id": item.default_supplier_id,
         "selling_price": _num(item.selling_price), "min_stock": _num(item.min_stock), "reorder_qty": _num(item.reorder_qty),
         "storage_location": item.storage_location, "compatibility": item.compatibility, "notes": item.notes, "is_active": item.is_active,
         "on_hand": _num(bal["on_hand"]), "reserved": _num(bal["reserved"]), "available": _num(available),
         "low_stock": bool(item.is_active and Decimal(item.min_stock) > 0 and available <= Decimal(item.min_stock)),
         "out_of_stock": bool(item.is_active and bal["on_hand"] <= 0)}
    if cats is not None:
        d["category"] = cats.get(item.category_id)
        d["subcategory"] = cats.get(item.subcategory_id)
    if _costs(user):  # purchase cost, average cost and stock value are not for every role
        d["purchase_price"] = _num(item.purchase_price)
        d["avg_cost"] = _num(inv.c4(bal["value"] / bal["on_hand"]) if bal["on_hand"] else ZERO)
        d["stock_value"] = _num(to_money(bal["value"]))
    return d


def _cat_names(db: DbSession) -> dict:
    return {c.id: {"id": c.id, "name_en": c.name_en, "name_ar": c.name_ar} for c in db.scalars(select(InventoryCategory))}


def _item_filter(q, *, text, category_id, active, low_stock, out_of_stock, in_stock, bal):
    if text:
        like = f"%{text.strip()}%"
        q = q.where(or_(InventoryItem.sku.ilike(like), InventoryItem.name_en.ilike(like), InventoryItem.name_ar.ilike(like), InventoryItem.barcode == text.strip(),
                        InventoryItem.oem_part_no.ilike(like), InventoryItem.mfr_part_no.ilike(like), InventoryItem.brand.ilike(like)))
    if category_id:
        q = q.where(or_(InventoryItem.category_id == category_id, InventoryItem.subcategory_id == category_id))
    if active is not None:
        q = q.where(InventoryItem.is_active == active)
    on_hand, reserved = func.coalesce(bal.c.on_hand, 0), func.coalesce(bal.c.reserved, 0)
    if low_stock:
        q = q.where(InventoryItem.is_active, InventoryItem.min_stock > 0, (on_hand - reserved) <= InventoryItem.min_stock)
    if out_of_stock:
        q = q.where(InventoryItem.is_active, on_hand <= 0)
    if in_stock:
        q = q.where(on_hand > 0)
    return q


def _balance_subquery(warehouse_id: int | None):
    q = select(InventoryBalance.item_id, func.sum(InventoryBalance.on_hand).label("on_hand"), func.sum(InventoryBalance.reserved).label("reserved")).group_by(InventoryBalance.item_id)
    if warehouse_id is not None:
        q = q.where(InventoryBalance.warehouse_id == warehouse_id)
    return q.subquery()


@router.get("/items")
def list_items(q: str | None = None, category_id: int | None = None, active: bool | None = None, low_stock: bool = False, out_of_stock: bool = False,
               in_stock: bool = False, warehouse_id: int | None = None, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
               user: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    bal = _balance_subquery(warehouse_id)
    base = select(InventoryItem).outerjoin(bal, bal.c.item_id == InventoryItem.id)
    base = _item_filter(base, text=q, category_id=category_id, active=active, low_stock=low_stock, out_of_stock=out_of_stock, in_stock=in_stock, bal=bal)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    items = list(db.scalars(base.order_by(InventoryItem.name_en).limit(limit).offset(offset)))
    balances, cats = _balances(db, [i.id for i in items], warehouse_id), _cat_names(db)
    return {"total": total, "items": [item_out(i, balances.get(i.id), user, cats) for i in items]}


@router.get("/available")
def available_for_jobs(q: str | None = None, warehouse_id: int | None = None, limit: int = Query(20, ge=1, le=100),
                       user: User = Depends(require("parts.write")), db: DbSession = Depends(get_db, scope="function")):
    """What an employee sees when adding a part 'From Warehouse' to a repair order: name, SKU, brand, available quantity, selling price."""
    wh = inv.get_warehouse(db, warehouse_id)
    bal = select(InventoryBalance.item_id, InventoryBalance.on_hand, InventoryBalance.reserved).where(InventoryBalance.warehouse_id == wh.id).subquery()
    base = select(InventoryItem, func.coalesce(bal.c.on_hand, 0), func.coalesce(bal.c.reserved, 0)).outerjoin(bal, bal.c.item_id == InventoryItem.id) \
        .where(InventoryItem.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        base = base.where(or_(InventoryItem.sku.ilike(like), InventoryItem.name_en.ilike(like), InventoryItem.name_ar.ilike(like), InventoryItem.barcode == q.strip(),
                              InventoryItem.oem_part_no.ilike(like), InventoryItem.mfr_part_no.ilike(like), InventoryItem.brand.ilike(like)))
    rows = db.execute(base.order_by(InventoryItem.name_en).limit(limit)).all()
    return [{"item_id": i.id, "sku": i.sku, "name_en": i.name_en, "name_ar": i.name_ar, "brand": i.brand, "warehouse_id": wh.id,
             "warehouse": {"en": wh.name_en, "ar": wh.name_ar}, "on_hand": _num(o), "reserved": _num(r), "available": _num(Decimal(o) - Decimal(r)),
             "selling_price": _num(i.selling_price), "uom": i.uom} for i, o, r in rows]


@router.post("/items", status_code=201)
def create_item(body: ItemIn, request: Request, user: User = Depends(WRITE), db: DbSession = Depends(get_db, scope="function")):
    data = _clean(body.model_dump())
    data["sku"] = data["sku"].upper()
    if db.scalar(select(InventoryItem.id).where(InventoryItem.sku == data["sku"])):
        raise AppError("كود الصنف (SKU) مستخدم", 409, "duplicate_sku")
    _validate_item(db, data)
    item = InventoryItem(**data, created_by=user.id)
    db.add(item)
    db.flush()
    audit(db, user, "inventory.item.create", "inventory_item", item.id, after=snapshot(item, ITEM_FIELDS), ip=client_ip(request))
    return item_out(item, None, user, _cat_names(db))


@router.get("/items/{item_id}")
def get_item_detail(item_id: int, user: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    item = inv.get_item(db, item_id)
    out = item_out(item, _balances(db, [item.id]).get(item.id), user, _cat_names(db))
    out["warehouses"] = [{"warehouse_id": b.warehouse_id, "on_hand": _num(b.on_hand), "reserved": _num(b.reserved), "available": _num(b.available),
                          **({"avg_cost": _num(inv.c4(b.avg_cost)), "value": _num(to_money(b.value)), "last_cost": _num(b.last_cost)} if _costs(user) else {})}
                         for b in db.scalars(select(InventoryBalance).where(InventoryBalance.item_id == item.id))]
    return out


@router.patch("/items/{item_id}")
def update_item(item_id: int, body: ItemPatch, request: Request, user: User = Depends(WRITE), db: DbSession = Depends(get_db, scope="function")):
    item = inv.get_item(db, item_id)
    before = snapshot(item, ITEM_FIELDS)
    changes = _clean(body.model_dump(exclude_unset=True))
    for required in ("name_en", "uom"):
        if required in changes and changes[required] is None:
            raise AppError("قيمة مطلوبة", 422, "required")
    merged = {**{f: getattr(item, f) for f in ITEM_FIELDS}, **changes}
    _validate_item(db, merged, exclude_id=item.id)
    for k, v in changes.items():
        setattr(item, k, v)
    audit(db, user, "inventory.item.update", "inventory_item", item.id, before=before, after=snapshot(item, ITEM_FIELDS), ip=client_ip(request))
    return item_out(item, _balances(db, [item.id]).get(item.id), user, _cat_names(db))


# ---- balances, ledger, low stock, valuation ---------------------------------------------------------------------------------------
@router.get("/balances")
def balances(warehouse_id: int | None = None, item_id: int | None = None, only_stock: bool = False, limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
             user: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    q = select(InventoryBalance, InventoryItem, Warehouse).join(InventoryItem, InventoryItem.id == InventoryBalance.item_id) \
        .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id)
    if warehouse_id:
        q = q.where(InventoryBalance.warehouse_id == warehouse_id)
    if item_id:
        q = q.where(InventoryBalance.item_id == item_id)
    if only_stock:
        q = q.where(InventoryBalance.on_hand > 0)
    rows = db.execute(q.order_by(InventoryItem.name_en, Warehouse.id).limit(limit).offset(offset)).all()
    out = []
    for b, i, w in rows:
        d = {"item_id": i.id, "sku": i.sku, "name_en": i.name_en, "name_ar": i.name_ar, "warehouse_id": w.id, "warehouse": w.name_en,
             "on_hand": _num(b.on_hand), "reserved": _num(b.reserved), "available": _num(b.available), "min_stock": _num(i.min_stock)}
        if _costs(user):
            d.update(avg_cost=_num(inv.c4(b.avg_cost)), last_cost=_num(b.last_cost), value=_num(to_money(b.value)))
        out.append(d)
    return out


def movement_out(m: StockMovement, user: User, extra: dict | None = None) -> dict:
    d = {"id": m.id, "ts": m.ts, "item_id": m.item_id, "warehouse_id": m.warehouse_id, "type": m.movement_type, "qty": _num(m.qty), "reserved_delta": _num(m.reserved_delta),
         "on_hand_after": _num(m.on_hand_after), "doc_type": m.doc_type, "doc_id": m.doc_id, "part_id": m.part_id, "visit_id": str(m.visit_id) if m.visit_id else None,
         "reason": m.reason, "user_id": str(m.user_id) if m.user_id else None, "reverses_id": m.reverses_id}
    if _costs(user):
        d.update(unit_cost=_num(m.unit_cost), value_delta=_num(m.value_delta), value_after=_num(m.value_after))
    if extra:
        d.update(extra)
    return d


def _period(date_from: date | None, date_to: date | None) -> tuple[datetime, datetime, date, date]:
    today = datetime.now(TZ).date()
    a, b = date_from or today.replace(day=1), date_to or today
    if b < a:
        raise AppError("تاريخ النهاية قبل البداية", 422, "bad_range")
    return datetime.combine(a, time.min, TZ), next_day_start(b, TZ), a, b


@router.get("/movements")
def movements(item_id: int | None = None, warehouse_id: int | None = None, type: str | None = None, part_id: int | None = None, visit_id: UUID | None = None,
              doc_type: str | None = None, doc_id: str | None = None, date_from: date | None = None, date_to: date | None = None,
              limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), user: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    q = select(StockMovement, InventoryItem.sku, InventoryItem.name_en).join(InventoryItem, InventoryItem.id == StockMovement.item_id)
    for col, val in ((StockMovement.item_id, item_id), (StockMovement.warehouse_id, warehouse_id), (StockMovement.movement_type, type.upper() if type else None),
                     (StockMovement.part_id, part_id), (StockMovement.visit_id, visit_id), (StockMovement.doc_type, doc_type), (StockMovement.doc_id, doc_id)):
        if val is not None:
            q = q.where(col == val)
    if date_from or date_to:
        start, end, _, _ = _period(date_from, date_to)
        q = q.where(StockMovement.ts >= start, StockMovement.ts < end)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(StockMovement.id.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [movement_out(m, user, {"sku": sku, "item_name": name}) for m, sku, name in rows]}


@router.get("/low-stock")
def low_stock(warehouse_id: int | None = None, user: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    bal = _balance_subquery(warehouse_id)
    q = select(InventoryItem, func.coalesce(bal.c.on_hand, 0), func.coalesce(bal.c.reserved, 0)).outerjoin(bal, bal.c.item_id == InventoryItem.id)
    q = _item_filter(q, text=None, category_id=None, active=True, low_stock=True, out_of_stock=False, in_stock=False, bal=bal)
    return [{"item_id": i.id, "sku": i.sku, "name_en": i.name_en, "name_ar": i.name_ar, "on_hand": _num(o), "reserved": _num(r), "available": _num(Decimal(o) - Decimal(r)),
             "min_stock": _num(i.min_stock), "reorder_qty": _num(i.reorder_qty),
             "suggested_order": _num(max(Decimal(i.reorder_qty), Decimal(i.min_stock) - (Decimal(o) - Decimal(r)))), "default_supplier_id": i.default_supplier_id}
            for i, o, r in db.execute(q.order_by(InventoryItem.name_en)).all()]


@router.get("/valuation")
def valuation(warehouse_id: int | None = None, _: User = Depends(COSTS), db: DbSession = Depends(get_db, scope="function")):
    q = select(InventoryBalance, InventoryItem).join(InventoryItem, InventoryItem.id == InventoryBalance.item_id).where(InventoryBalance.on_hand > 0)
    if warehouse_id:
        q = q.where(InventoryBalance.warehouse_id == warehouse_id)
    rows = [{"item_id": i.id, "sku": i.sku, "name_en": i.name_en, "warehouse_id": b.warehouse_id, "on_hand": _num(b.on_hand), "avg_cost": _num(inv.c4(b.avg_cost)),
             "value": _num(to_money(b.value))} for b, i in db.execute(q.order_by(InventoryItem.name_en)).all()]
    return {"total_value": _num(sum((Decimal(r["value"]) for r in rows), Decimal("0.00"))), "method": "perpetual weighted average", "items": rows}


@router.get("/valuation-trend")
def valuation_trend(months: int = Query(6, ge=1, le=24), date_to: date | None = None, _: User = Depends(COSTS), db: DbSession = Depends(get_db, scope="function")):
    """Inventory value at the end of each of the last `months` months (the current month ends at date_to's day).
    Read from the append-only ledger: the running value_after of the latest movement of every item/warehouse before the cut-off."""
    end_day = date_to or datetime.now(TZ).date()
    points = []
    y, m = end_day.year, end_day.month
    for _i in range(months):
        last = end_day if (y, m) == (end_day.year, end_day.month) else (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
        cutoff = next_day_start(last, TZ)
        latest = (select(StockMovement.value_after,
                         func.row_number().over(partition_by=(StockMovement.item_id, StockMovement.warehouse_id), order_by=(StockMovement.ts.desc(), StockMovement.id.desc())).label("rn"))
                  .where(StockMovement.ts < cutoff).subquery())
        total = db.scalar(select(func.coalesce(func.sum(latest.c.value_after), 0)).where(latest.c.rn == 1)) or Decimal("0")
        points.append({"month": f"{y:04d}-{m:02d}", "as_of": last.isoformat(), "value": _num(to_money(total))})
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    points.reverse()
    return {"points": points, "source": "stock ledger (running value after each movement)"}


@router.get("/dashboard")
def dashboard(date_from: date | None = None, date_to: date | None = None, user: User = Depends(READ), db: DbSession = Depends(get_db, scope="function")):
    start, end, a, b = _period(date_from, date_to)
    bal = _balance_subquery(None)
    active_items = db.scalar(select(func.count()).select_from(InventoryItem).where(InventoryItem.is_active))
    qty = db.scalar(select(func.coalesce(func.sum(InventoryBalance.on_hand), 0)))
    low = db.scalar(select(func.count()).select_from(_item_filter(select(InventoryItem.id).outerjoin(bal, bal.c.item_id == InventoryItem.id), text=None, category_id=None,
                                                                   active=True, low_stock=True, out_of_stock=False, in_stock=False, bal=bal).subquery()))
    out = db.scalar(select(func.count()).select_from(_item_filter(select(InventoryItem.id).outerjoin(bal, bal.c.item_id == InventoryItem.id), text=None, category_id=None,
                                                                  active=True, low_stock=False, out_of_stock=True, in_stock=False, bal=bal).subquery()))
    received = db.scalar(select(func.coalesce(func.sum(StockMovement.qty), 0)).where(StockMovement.movement_type == "GOODS_RECEIPT", StockMovement.ts >= start, StockMovement.ts < end))
    reversed_in = db.scalar(select(func.coalesce(func.sum(StockMovement.qty), 0)).where(StockMovement.movement_type == "REVERSAL", StockMovement.doc_type == "goods_receipt",
                                                                                    StockMovement.ts >= start, StockMovement.ts < end))
    issued = db.scalar(select(func.coalesce(func.sum(-StockMovement.qty), 0)).where(StockMovement.movement_type == "ISSUE", StockMovement.ts >= start, StockMovement.ts < end))
    returned = db.scalar(select(func.coalesce(func.sum(StockMovement.qty), 0)).where(StockMovement.movement_type == "RETURN_TO_WAREHOUSE", StockMovement.ts >= start, StockMovement.ts < end))
    d = {"period": {"from": a, "to": b}, "total_items": active_items, "total_stock_qty": _num(qty), "low_stock_items": low, "out_of_stock_items": out,
         "stock_received": _num(Decimal(received) + Decimal(reversed_in)), "stock_issued": _num(Decimal(issued) - Decimal(returned)),
         "links": {"total_items": "/api/inventory/items?active=true", "low_stock_items": "/api/inventory/items?low_stock=true", "out_of_stock_items": "/api/inventory/items?out_of_stock=true",
                   "stock_received": "/api/inventory/movements?type=GOODS_RECEIPT", "stock_issued": "/api/inventory/movements?type=ISSUE",
                   "total_stock_qty": "/api/inventory/balances?only_stock=true"}}
    if _costs(user):
        d["inventory_value"] = _num(to_money(db.scalar(select(func.coalesce(func.sum(InventoryBalance.value), 0)))))
        d["links"]["inventory_value"] = "/api/inventory/valuation"
    if "purchasing.read" in user.permissions:
        posted = to_money(db.scalar(select(func.coalesce(func.sum(PurchaseInvoice.subtotal - PurchaseInvoice.discount), 0))
                                    .where(PurchaseInvoice.status == "posted", PurchaseInvoice.posted_at >= start, PurchaseInvoice.posted_at < end)))
        d["inventory_purchases"] = _num(posted)
        d["links"]["inventory_purchases"] = "/api/inventory/purchase-invoices?status=posted"
    return d


# ---- opening balance, adjustments, counts, transfers, supplier returns, reversal ------------------------------------------------------
class OpeningIn(BaseModel):
    item_id: int
    warehouse_id: int | None = None
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=4)


@router.post("/opening-balances", status_code=201)
def opening(body: OpeningIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(ADJUST), db: DbSession = Depends(get_db, scope="function")):
    item = inv.get_item(db, body.item_id, active=True)
    wh = inv.get_warehouse(db, body.warehouse_id)
    mv = inv.opening_balance(db, item.id, wh.id, body.qty, body.unit_cost, user, idempotency_key)
    audit(db, user, "inventory.opening", "inventory_item", item.id, after={"qty": str(body.qty), "unit_cost": str(body.unit_cost)}, ip=client_ip(request))
    return movement_out(mv, user)


class AdjLine(BaseModel):
    item_id: int
    qty_delta: Decimal = Field(max_digits=14, decimal_places=3)


class AdjustmentIn(BaseModel):
    warehouse_id: int | None = None
    reason: str = Field(min_length=3)
    lines: list[AdjLine] = Field(min_length=1)


class CountLine(BaseModel):
    item_id: int
    counted_qty: Decimal = Field(ge=0, max_digits=14, decimal_places=3)


class CountIn(BaseModel):
    warehouse_id: int | None = None
    reason: str = Field("physical count", min_length=3)
    lines: list[CountLine] = Field(min_length=1)


def adjustment_out(db: DbSession, adj: StockAdjustment, user: User) -> dict:
    lines = db.scalars(select(StockAdjustmentLine).where(StockAdjustmentLine.adjustment_id == adj.id).order_by(StockAdjustmentLine.id))
    return {"id": str(adj.id), "number": adj.number, "kind": adj.kind, "warehouse_id": adj.warehouse_id, "reason": adj.reason, "created_at": adj.created_at,
            "lines": [{"item_id": l.item_id, "system_qty": _num(l.system_qty), "counted_qty": _num(l.counted_qty), "qty_delta": _num(l.qty_delta), "movement_id": l.movement_id,
                       **({"unit_cost": _num(l.unit_cost)} if _costs(user) else {})} for l in lines]}


@router.post("/adjustments", status_code=201)
def create_adjustment(body: AdjustmentIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(ADJUST), db: DbSession = Depends(get_db, scope="function")):
    wh = inv.get_warehouse(db, body.warehouse_id)
    adj = inv.adjust(db, wh.id, [l.model_dump() for l in body.lines], body.reason, user, idempotency_key)
    audit(db, user, "inventory.adjustment", "stock_adjustment", adj.id, after={"lines": len(body.lines)}, reason=body.reason, ip=client_ip(request))
    return adjustment_out(db, adj, user)


@router.post("/counts", status_code=201)
def create_count(body: CountIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(ADJUST), db: DbSession = Depends(get_db, scope="function")):
    wh = inv.get_warehouse(db, body.warehouse_id)
    adj = inv.physical_count(db, wh.id, [l.model_dump() for l in body.lines], body.reason, user, idempotency_key)
    audit(db, user, "inventory.count", "stock_adjustment", adj.id, after={"lines": len(body.lines)}, reason=body.reason, ip=client_ip(request))
    return adjustment_out(db, adj, user)


class TransferLine(BaseModel):
    item_id: int
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)


class TransferIn(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    reason: str = Field("warehouse transfer", min_length=3)
    lines: list[TransferLine] = Field(min_length=1)


@router.post("/transfers", status_code=201)
def create_transfer(body: TransferIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(ADJUST), db: DbSession = Depends(get_db, scope="function")):
    doc = inv.transfer(db, body.from_warehouse_id, body.to_warehouse_id, [l.model_dump() for l in body.lines], body.reason, user, idempotency_key)
    audit(db, user, "inventory.transfer", "stock_transfer", doc, after={"lines": len(body.lines)}, reason=body.reason, ip=client_ip(request))
    return {"document_id": doc, "movements": [movement_out(m, user) for m in db.scalars(select(StockMovement).where(StockMovement.doc_type == "transfer", StockMovement.doc_id == doc).order_by(StockMovement.id))]}


class SupplierReturnIn(BaseModel):
    item_id: int
    warehouse_id: int | None = None
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    supplier_id: int
    credit_amount: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    invoice_id: UUID | None = None
    reason: str = Field(min_length=3)


@router.post("/supplier-returns", status_code=201)
def supplier_return(body: SupplierReturnIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(require("inventory.adjust")),
                    db: DbSession = Depends(get_db, scope="function")):
    wh = inv.get_warehouse(db, body.warehouse_id)
    mv = pur.supplier_return(db, item_id=body.item_id, warehouse_id=wh.id, qty=body.qty, supplier_id=body.supplier_id, credit_amount=body.credit_amount,
                             invoice_id=body.invoice_id, reason=body.reason, user=user, key=idempotency_key)
    audit(db, user, "inventory.supplier_return", "stock_movement", mv.id, after={"qty": str(body.qty), "credit": str(body.credit_amount)}, reason=body.reason, ip=client_ip(request))
    return movement_out(mv, user)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3)


@router.post("/movements/{mid}/reverse", status_code=201)
def reverse(mid: int, body: ReasonIn, request: Request, user: User = Depends(ADJUST), db: DbSession = Depends(get_db, scope="function")):
    mv = inv.reverse_movement(db, mid, body.reason, user)
    audit(db, user, "inventory.reverse", "stock_movement", mid, after={"reversal": mv.id}, reason=body.reason, ip=client_ip(request))
    return movement_out(mv, user)


# ---- purchase invoices ---------------------------------------------------------------------------------------------------------------
class PLine(BaseModel):
    item_id: int
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    discount: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class PurchaseInvoiceIn(BaseModel):
    supplier_id: int
    supplier_invoice_no: str = Field(min_length=1, max_length=100)
    invoice_date: date
    warehouse_id: int | None = None
    discount: Decimal = Field(Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    tax_rate: Decimal = Field(Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)
    notes: str | None = None
    lines: list[PLine] = Field(min_length=1)


class PurchaseInvoicePatch(BaseModel):
    supplier_invoice_no: str | None = Field(None, min_length=1, max_length=100)
    invoice_date: date | None = None
    warehouse_id: int | None = None
    discount: Decimal | None = Field(None, ge=0, max_digits=14, decimal_places=2)
    tax_rate: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    notes: str | None = None
    lines: list[PLine] | None = Field(None, min_length=1)


def _line_dicts(lines: list[PLine]) -> list[dict]:
    return [{"item_id": l.item_id, "qty": l.qty, "unit_cost": l.unit_cost, "discount": l.discount} for l in lines]


def invoice_out(db: DbSession, inv_: PurchaseInvoice) -> dict:
    lines = list(db.execute(select(PurchaseInvoiceLine, InventoryItem.sku, InventoryItem.name_en, InventoryItem.name_ar)
                            .join(InventoryItem, InventoryItem.id == PurchaseInvoiceLine.item_id).where(PurchaseInvoiceLine.invoice_id == inv_.id).order_by(PurchaseInvoiceLine.id)))
    receipts = list(db.scalars(select(GoodsReceipt).where(GoodsReceipt.invoice_id == inv_.id).order_by(GoodsReceipt.number)))
    payments = list(db.scalars(select(SupplierPayment).where(SupplierPayment.invoice_id == inv_.id).order_by(SupplierPayment.id)))
    credits = list(db.scalars(select(SupplierCredit).where(SupplierCredit.invoice_id == inv_.id).order_by(SupplierCredit.id)))
    supplier = db.get(Supplier, inv_.supplier_id)
    m = pur.money(db, inv_)
    return {"id": str(inv_.id), "number": inv_.number, "supplier_id": inv_.supplier_id, "supplier": supplier.name if supplier else None,
            "supplier_invoice_no": inv_.supplier_invoice_no, "invoice_date": inv_.invoice_date, "warehouse_id": inv_.warehouse_id, "status": inv_.status,
            "receipt_status": inv_.receipt_status, "payment_status": m["payment_status"], "subtotal": _num(inv_.subtotal), "discount": _num(inv_.discount),
            "tax_rate": _num(inv_.tax_rate), "tax_amount": _num(inv_.tax_amount), "total": _num(inv_.total), "paid": _num(m["paid"]), "credits": _num(m["credits"]),
            "outstanding": _num(m["outstanding"]), "notes": inv_.notes, "posted_at": inv_.posted_at, "cancelled_at": inv_.cancelled_at, "cancel_reason": inv_.cancel_reason,
            "lines": [{"id": l.id, "item_id": l.item_id, "sku": sku, "name_en": en, "name_ar": ar, "qty_ordered": _num(l.qty_ordered), "qty_received": _num(l.qty_received),
                       "qty_open": _num(Decimal(l.qty_ordered) - Decimal(l.qty_received)), "unit_cost": _num(l.unit_cost), "discount": _num(l.discount),
                       "line_total": _num(l.line_total)} for l, sku, en, ar in lines],
            "receipts": [{"id": str(r.id), "number": r.number, "status": r.status, "received_at": r.received_at, "notes": r.notes} for r in receipts],
            "payments": [{"id": p.id, "amount": _num(p.amount), "method": p.method, "reference": p.reference, "paid_at": p.paid_at} for p in payments],
            "supplier_credits": [{"id": c.id, "amount": _num(c.amount), "reason": c.reason, "created_at": c.created_at} for c in credits]}


def _get_invoice(db: DbSession, invoice_id: UUID) -> PurchaseInvoice:
    inv_ = db.get(PurchaseInvoice, invoice_id)
    if not inv_:
        raise AppError("فاتورة المشتريات غير موجودة", 404, "not_found")
    return inv_


@router.post("/purchase-invoices", status_code=201)
def create_purchase_invoice(body: PurchaseInvoiceIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(PUR_WRITE),
                            db: DbSession = Depends(get_db, scope="function")):
    invoice = pur.create_draft(db, supplier_id=body.supplier_id, supplier_invoice_no=body.supplier_invoice_no, invoice_date=body.invoice_date, warehouse_id=body.warehouse_id,
                               lines=_line_dicts(body.lines), discount=body.discount, tax_rate=body.tax_rate, notes=body.notes, user=user, key=idempotency_key)
    audit(db, user, "purchase.create", "purchase_invoice", invoice.id, after={"supplier_invoice_no": invoice.supplier_invoice_no, "total": str(invoice.total)}, ip=client_ip(request))
    return invoice_out(db, invoice)


@router.get("/purchase-invoices")
def list_purchase_invoices(supplier_id: int | None = None, status: str | None = None, receipt_status: str | None = None, payment_status: str | None = None,
                           date_from: date | None = None, date_to: date | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                           _: User = Depends(PUR_READ), db: DbSession = Depends(get_db, scope="function")):
    q = select(PurchaseInvoice)
    if supplier_id:
        q = q.where(PurchaseInvoice.supplier_id == supplier_id)
    if status:
        q = q.where(PurchaseInvoice.status == status)
    if receipt_status:
        q = q.where(PurchaseInvoice.receipt_status == receipt_status)
    if date_from:
        q = q.where(PurchaseInvoice.invoice_date >= date_from)
    if date_to:
        q = q.where(PurchaseInvoice.invoice_date <= date_to)
    rows = [invoice_out(db, i) for i in db.scalars(q.order_by(PurchaseInvoice.number.desc()).limit(limit).offset(offset))]
    if payment_status:
        rows = [r for r in rows if r["payment_status"] == payment_status]
    return rows


@router.get("/purchase-invoices/{invoice_id}")
def get_purchase_invoice(invoice_id: UUID, _: User = Depends(PUR_READ), db: DbSession = Depends(get_db, scope="function")):
    return invoice_out(db, _get_invoice(db, invoice_id))


@router.patch("/purchase-invoices/{invoice_id}")
def update_purchase_invoice(invoice_id: UUID, body: PurchaseInvoicePatch, request: Request, user: User = Depends(PUR_WRITE), db: DbSession = Depends(get_db, scope="function")):
    data = body.model_dump(exclude_unset=True)
    lines = _line_dicts(body.lines) if body.lines is not None else None
    invoice = pur.update_draft(db, invoice_id, supplier_invoice_no=data.get("supplier_invoice_no"), invoice_date=data.get("invoice_date"), warehouse_id=data.get("warehouse_id"),
                               lines=lines, discount=data.get("discount"), tax_rate=data.get("tax_rate"), notes=data.get("notes"))
    audit(db, user, "purchase.update", "purchase_invoice", invoice.id, after={"total": str(invoice.total)}, ip=client_ip(request))
    return invoice_out(db, invoice)


@router.delete("/purchase-invoices/{invoice_id}")
def delete_purchase_invoice(invoice_id: UUID, request: Request, user: User = Depends(PUR_WRITE), db: DbSession = Depends(get_db, scope="function")):
    pur.delete_draft(db, invoice_id)
    audit(db, user, "purchase.delete_draft", "purchase_invoice", invoice_id, ip=client_ip(request))
    return {"deleted": True}


@router.post("/purchase-invoices/{invoice_id}/post")
def post_purchase_invoice(invoice_id: UUID, request: Request, user: User = Depends(PUR_WRITE), db: DbSession = Depends(get_db, scope="function")):
    invoice = pur.post_invoice(db, invoice_id)
    audit(db, user, "purchase.post", "purchase_invoice", invoice.id, after={"total": str(invoice.total)}, ip=client_ip(request))
    return invoice_out(db, invoice)


@router.post("/purchase-invoices/{invoice_id}/cancel")
def cancel_purchase_invoice(invoice_id: UUID, body: ReasonIn, request: Request, user: User = Depends(PUR_WRITE), db: DbSession = Depends(get_db, scope="function")):
    invoice = pur.cancel_invoice(db, invoice_id, body.reason)
    audit(db, user, "purchase.cancel", "purchase_invoice", invoice.id, reason=body.reason, ip=client_ip(request))
    return invoice_out(db, invoice)


class ReceiptLineIn(BaseModel):
    invoice_line_id: int
    qty: Decimal = Field(gt=0, max_digits=14, decimal_places=3)


class ReceiptIn(BaseModel):
    lines: list[ReceiptLineIn] = Field(min_length=1)
    notes: str | None = None


@router.post("/purchase-invoices/{invoice_id}/receipts", status_code=201)
def receive(invoice_id: UUID, body: ReceiptIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(PUR_WRITE),
            db: DbSession = Depends(get_db, scope="function")):
    receipt = pur.receive_goods(db, invoice_id, [l.model_dump() for l in body.lines], user, idempotency_key, body.notes)
    audit(db, user, "purchase.receive", "goods_receipt", receipt.id, after={"invoice": str(invoice_id), "lines": len(body.lines)}, ip=client_ip(request))
    return receipt_out(db, receipt)


def receipt_out(db: DbSession, r: GoodsReceipt) -> dict:
    lines = db.execute(select(GoodsReceiptLine, InventoryItem.sku, InventoryItem.name_en).join(InventoryItem, InventoryItem.id == GoodsReceiptLine.item_id)
                       .where(GoodsReceiptLine.receipt_id == r.id).order_by(GoodsReceiptLine.id)).all()
    return {"id": str(r.id), "number": r.number, "invoice_id": str(r.invoice_id), "status": r.status, "received_at": r.received_at, "notes": r.notes,
            "lines": [{"invoice_line_id": l.invoice_line_id, "item_id": l.item_id, "sku": sku, "name_en": name, "qty": _num(l.qty), "unit_cost": _num(l.unit_cost),
                       "value": _num(l.value)} for l, sku, name in lines]}


@router.get("/receipts")
def list_receipts(invoice_id: UUID | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), _: User = Depends(PUR_READ),
                  db: DbSession = Depends(get_db, scope="function")):
    q = select(GoodsReceipt)
    if invoice_id:
        q = q.where(GoodsReceipt.invoice_id == invoice_id)
    return [receipt_out(db, r) for r in db.scalars(q.order_by(GoodsReceipt.number.desc()).limit(limit).offset(offset))]


@router.post("/receipts/{receipt_id}/reverse")
def reverse_receipt(receipt_id: UUID, body: ReasonIn, request: Request, user: User = Depends(PUR_WRITE), db: DbSession = Depends(get_db, scope="function")):
    receipt = pur.reverse_receipt(db, receipt_id, body.reason, user)
    audit(db, user, "purchase.receipt_reverse", "goods_receipt", receipt.id, reason=body.reason, ip=client_ip(request))
    return receipt_out(db, receipt)


class SupplierPaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: str
    reference: str | None = None
    note: str | None = None


@router.post("/purchase-invoices/{invoice_id}/payments", status_code=201)
def pay_supplier(invoice_id: UUID, body: SupplierPaymentIn, request: Request, idempotency_key: str | None = IDEM, user: User = Depends(PUR_WRITE),
                 db: DbSession = Depends(get_db, scope="function")):
    if body.method not in cfg.payment_method_keys(db):
        raise AppError("طريقة الدفع غير معروفة", 422, "bad_method")
    pay = pur.pay_invoice(db, invoice_id, amount=body.amount, method=body.method, reference=body.reference, note=body.note, user=user, key=idempotency_key)
    audit(db, user, "purchase.payment", "supplier_payment", pay.id, after={"invoice": str(invoice_id), "amount": f"{Decimal(pay.amount):.2f}"}, ip=client_ip(request))
    return {"id": pay.id, "invoice_id": str(pay.invoice_id), "amount": _num(pay.amount), "method": pay.method, "reference": pay.reference, "paid_at": pay.paid_at,
            "invoice": invoice_out(db, _get_invoice(db, invoice_id))}


@router.get("/supplier-balances")
def supplier_balances(_: User = Depends(PUR_READ), db: DbSession = Depends(get_db, scope="function")):
    return [{**{k: (_num(v) if isinstance(v, Decimal) else v) for k, v in row.items()}} for row in pur.supplier_balances(db)]
