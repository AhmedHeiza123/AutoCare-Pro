import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Technician(Base):
    __tablename__ = "technicians"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    specialization: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TechnicianAssignment(Base):
    """Multiple technicians per job card."""

    __tablename__ = "technician_assignments"
    __table_args__ = (UniqueConstraint("visit_id", "technician_id", name="uq_assignment"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id", ondelete="RESTRICT"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class JobStatusHistory(Base):
    __tablename__ = "job_status_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(Text)


class RepairOperation(Base):
    __tablename__ = "repair_operations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    category: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending|in_progress|done|cancelled
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    labor_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    labor_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    labor_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Inspection(Base):
    __tablename__ = "inspections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), index=True)
    category: Mapped[str] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InspectionItem(Base):
    __tablename__ = "inspection_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))  # good|attention|critical|na
    note: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    estimate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class ReceptionRecord(Base):
    """Vehicle condition captured at check-in (one per visit)."""

    __tablename__ = "reception_records"
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicle_visits.id", ondelete="RESTRICT"), primary_key=True)
    fuel_level: Mapped[str | None] = mapped_column(String(20))
    condition: Mapped[dict | None] = mapped_column(JSONB)  # {point: {state, note}}
    complaints: Mapped[list | None] = mapped_column(JSONB)  # [{category, text}]
    belongings: Mapped[list | None] = mapped_column(JSONB)
    dashboard_lights: Mapped[list | None] = mapped_column(JSONB)  # warning lights that were on at check-in
    notes: Mapped[str | None] = mapped_column(Text)
