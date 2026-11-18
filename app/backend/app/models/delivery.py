import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class QualityCheck(Base):
    __tablename__ = "quality_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    result: Mapped[str] = mapped_column(String(10))  # passed | failed
    repairs_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    parts_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    road_test_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    override_reason: Mapped[str | None] = mapped_column(Text)
    checked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Delivery(Base):
    """One row per delivery event (a reopened job can be delivered again; earlier rows stay as history)."""

    __tablename__ = "deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    final_mileage: Mapped[int] = mapped_column(Integer)
    final_condition: Mapped[str | None] = mapped_column(Text)
    ack_name: Mapped[str] = mapped_column(String(200))
    ack_note: Mapped[str | None] = mapped_column(Text)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"))
    payment_status: Mapped[str | None] = mapped_column(String(20))
    overridden: Mapped[dict | None] = mapped_column(JSONB)  # blockers that a manager overrode
    override_reason: Mapped[str | None] = mapped_column(Text)
    delivered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class Warranty(Base):
    __tablename__ = "warranties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(10))  # part | labor | operation
    part_id: Mapped[int | None] = mapped_column(ForeignKey("part_purchases.id", ondelete="RESTRICT"))
    operation_id: Mapped[int | None] = mapped_column(ForeignKey("repair_operations.id", ondelete="RESTRICT"))
    description: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    start_mileage: Mapped[int | None] = mapped_column(Integer)
    mileage_limit: Mapped[int | None] = mapped_column(Integer)
    coverage: Mapped[str | None] = mapped_column(Text)
    exclusions: Mapped[str | None] = mapped_column(Text)
    is_void: Mapped[bool] = mapped_column(Boolean, default=False)
    void_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warranty_id: Mapped[int] = mapped_column(ForeignKey("warranties.id", ondelete="RESTRICT"), index=True)
    claim_date: Mapped[date] = mapped_column(Date)
    mileage: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | approved | rejected
    resolution: Mapped[str | None] = mapped_column(Text)
    repair_visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceReminder(Base):
    __tablename__ = "maintenance_reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    due_mileage: Mapped[int | None] = mapped_column(Integer)
    source_visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | done | dismissed
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
