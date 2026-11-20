"""Workshop inventory: catalog, warehouses, balances, the stock-movement ledger, reservations, purchase invoices, goods receipts,
supplier payments/credits and stock adjustments. See docs/INVENTORY_MODULE.md for the rules."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, Integer, Numeric, String, Text, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

QTY = Numeric(14, 3)
COST = Numeric(14, 4)
MONEY = Numeric(14, 2)
VALUE = Numeric(16, 4)


class InventoryCategory(Base):
    __tablename__ = "inventory_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_categories.id", ondelete="RESTRICT"), index=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Warehouse(Base):
    __tablename__ = "warehouses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class InventoryItem(Base):
    """Master record of a spare part kept in stock (one row per part, however many suppliers/purchase prices it has)."""
    __tablename__ = "inventory_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True)  # stored upper-case
    name_en: Mapped[str] = mapped_column(String(200))
    name_ar: Mapped[str | None] = mapped_column(String(200))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_categories.id", ondelete="RESTRICT"), index=True)
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_categories.id", ondelete="RESTRICT"))
    brand: Mapped[str | None] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(100))
    mfr_part_no: Mapped[str | None] = mapped_column(String(100))
    oem_part_no: Mapped[str | None] = mapped_column(String(100), index=True)
    barcode: Mapped[str | None] = mapped_column(String(64))
    uom: Mapped[str] = mapped_column(String(20), default="pcs", server_default="pcs")
    default_supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    purchase_price: Mapped[Decimal] = mapped_column(COST, default=Decimal("0"), server_default="0")  # reference price; real cost = average cost
    selling_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default="0")
    min_stock: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    reorder_qty: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    storage_location: Mapped[str | None] = mapped_column(String(100))
    compatibility: Mapped[list | None] = mapped_column(JSONB)  # optional list of vehicle makes/models/years
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InventoryBalance(Base):
    """Current position of one item in one warehouse. Only the posting engine writes here."""
    __tablename__ = "inventory_balances"
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"), primary_key=True)
    on_hand: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    reserved: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    value: Mapped[Decimal] = mapped_column(VALUE, default=Decimal("0"), server_default="0")  # total inventory value (weighted average)
    last_cost: Mapped[Decimal] = mapped_column(COST, default=Decimal("0"), server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def available(self) -> Decimal:
        return Decimal(self.on_hand) - Decimal(self.reserved)

    @property
    def avg_cost(self) -> Decimal:
        return (Decimal(self.value) / Decimal(self.on_hand)) if Decimal(self.on_hand) else Decimal("0")


MOVEMENT_TYPES = ("OPENING", "GOODS_RECEIPT", "RESERVE", "RELEASE", "ISSUE", "RETURN_TO_WAREHOUSE", "SUPPLIER_RETURN",
                  "ADJUSTMENT", "COUNT", "TRANSFER_OUT", "TRANSFER_IN", "REVERSAL")


class StockMovement(Base):
    """Append-only ledger (a database trigger rejects UPDATE and DELETE). Corrections are new REVERSAL rows."""
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(BigInteger, Identity(start=1), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    movement_type: Mapped[str] = mapped_column(String(24))
    qty: Mapped[Decimal] = mapped_column(QTY)  # signed change of on-hand stock
    reserved_delta: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    unit_cost: Mapped[Decimal] = mapped_column(COST, default=Decimal("0"), server_default="0")
    value_delta: Mapped[Decimal] = mapped_column(VALUE, default=Decimal("0"), server_default="0")
    on_hand_after: Mapped[Decimal] = mapped_column(QTY)
    value_after: Mapped[Decimal] = mapped_column(VALUE)
    doc_type: Mapped[str | None] = mapped_column(String(30))
    doc_id: Mapped[str | None] = mapped_column(String(64))
    part_id: Mapped[int | None] = mapped_column(ForeignKey("part_purchases.id", ondelete="RESTRICT"), index=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    reverses_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id", ondelete="RESTRICT"), unique=True)


class StockReservation(Base):
    """Stock held for an approved repair-order part. One active reservation per job part."""
    __tablename__ = "stock_reservations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    part_id: Mapped[int] = mapped_column(ForeignKey("part_purchases.id", ondelete="RESTRICT"), index=True)
    qty: Mapped[Decimal] = mapped_column(QTY)
    status: Mapped[str] = mapped_column(String(12), default="active")  # active | consumed | released
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int] = mapped_column(Integer, Identity(start=1), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    supplier_invoice_no: Mapped[str] = mapped_column(String(100))
    invoice_date: Mapped[date] = mapped_column(Date)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | posted | cancelled
    receipt_status: Mapped[str] = mapped_column(String(12), default="none", server_default="none")  # none | partial | full
    subtotal: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default="0")
    discount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default="0")
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), server_default="0")
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default="0")
    total: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseInvoiceLine(Base):
    __tablename__ = "purchase_invoice_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_invoices.id", ondelete="RESTRICT"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    qty_ordered: Mapped[Decimal] = mapped_column(QTY)
    qty_received: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), server_default="0")
    received_value: Mapped[Decimal] = mapped_column(VALUE, default=Decimal("0"), server_default="0")
    unit_cost: Mapped[Decimal] = mapped_column(COST)
    discount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default="0")  # line discount (amount)
    line_total: Mapped[Decimal] = mapped_column(MONEY)


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int] = mapped_column(Integer, Identity(start=1), unique=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_invoices.id", ondelete="RESTRICT"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(12), default="posted")  # posted | reversed
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    received_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    notes: Mapped[str | None] = mapped_column(Text)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reverse_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goods_receipts.id", ondelete="RESTRICT"), index=True)
    invoice_line_id: Mapped[int] = mapped_column(ForeignKey("purchase_invoice_lines.id", ondelete="RESTRICT"))
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"))
    qty: Mapped[Decimal] = mapped_column(QTY)
    unit_cost: Mapped[Decimal] = mapped_column(COST)  # net landed cost (after line and invoice discount)
    value: Mapped[Decimal] = mapped_column(VALUE)
    movement_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id", ondelete="RESTRICT"))


class SupplierPayment(Base):
    """Money paid to a supplier against a purchase invoice. Independent of goods receipts; never deleted."""
    __tablename__ = "supplier_payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_invoices.id", ondelete="RESTRICT"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    method: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)


class SupplierCredit(Base):
    """Credit received from a supplier (e.g. for goods returned). Reduces what we owe on the invoice / supplier."""
    __tablename__ = "supplier_credits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("purchase_invoices.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    reason: Mapped[str] = mapped_column(Text)
    movement_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int] = mapped_column(Integer, Identity(start=1), unique=True)
    kind: Mapped[str] = mapped_column(String(12))  # adjustment | count
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)


class StockAdjustmentLine(Base):
    __tablename__ = "stock_adjustment_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adjustment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_adjustments.id", ondelete="RESTRICT"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"))
    system_qty: Mapped[Decimal] = mapped_column(QTY)
    counted_qty: Mapped[Decimal | None] = mapped_column(QTY)
    qty_delta: Mapped[Decimal] = mapped_column(QTY)
    unit_cost: Mapped[Decimal] = mapped_column(COST)
    movement_id: Mapped[int | None] = mapped_column(ForeignKey("stock_movements.id", ondelete="RESTRICT"))
