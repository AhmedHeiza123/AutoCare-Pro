import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Identity, Integer, Numeric, String, Text,
                        func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    contact_person: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PartPurchase(Base):
    """A part bought externally for one job (no stock/inventory)."""

    __tablename__ = "part_purchases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    operation_id: Mapped[int | None] = mapped_column(ForeignKey("repair_operations.id", ondelete="RESTRICT"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    part_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    brand: Mapped[str | None] = mapped_column(String(100))
    part_number: Mapped[str | None] = mapped_column(String(100), index=True)
    supplier_invoice_no: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="requested")
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))  # warehouse parts: weighted-average cost at issue
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    # where the part comes from: direct = bought for this job (the original workflow), warehouse = issued from stock,
    # customer = supplied by the customer (no cost, no parts revenue)
    source: Mapped[str] = mapped_column(String(12), default="direct", server_default="direct")
    inventory_item_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    issued_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"), server_default="0")
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    installed_by: Mapped[int | None] = mapped_column(ForeignKey("technicians.id", ondelete="RESTRICT"))
    warranty_months: Mapped[int | None] = mapped_column(Integer)
    warranty_expiry: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PartReturn(Base):
    __tablename__ = "part_returns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part_purchases.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    # supplier / warehouse = the cost is recovered (COGS is reduced); defective / used = nothing is recovered (the cost stays)
    disposition: Mapped[str] = mapped_column(String(12), default="supplier", server_default="supplier")
    reason: Mapped[str | None] = mapped_column(Text)
    returned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    returned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_no: Mapped[int] = mapped_column(Integer, Identity(start=5000), unique=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    valid_until: Mapped[date | None] = mapped_column(Date)
    terms: Mapped[str | None] = mapped_column(Text)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), index=True)
    operation_id: Mapped[int | None] = mapped_column(ForeignKey("repair_operations.id", ondelete="RESTRICT"))
    part_id: Mapped[int | None] = mapped_column(ForeignKey("part_purchases.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(10))  # labor | part | other
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    approval_state: Mapped[str] = mapped_column(String(10), default="pending")  # pending|approved|rejected


class Approval(Base):
    """One customer decision on a quotation (whole quote or specific items), with evidence."""

    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), index=True)
    item_ids: Mapped[str] = mapped_column(Text)  # comma-separated quotation item ids covered
    decision: Mapped[str] = mapped_column(String(10))  # approved | rejected
    method: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
