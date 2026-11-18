import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, DateTime, ForeignKey, Identity, Index, Integer, Numeric, String,
                        Text, func, text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_no: Mapped[int] = mapped_column(Integer, Identity(start=1000), unique=True)
    customer_type: Mapped[str] = mapped_column(String(20), default="individual")  # individual|company
    full_name: Mapped[str] = mapped_column(String(200))
    company_name: Mapped[str | None] = mapped_column(String(200))
    mobile: Mapped[str] = mapped_column(String(40))
    mobile_compact: Mapped[str] = mapped_column(String(40), index=True)
    alt_phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    tax_number: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_no: Mapped[int] = mapped_column(Integer, Identity(start=1), unique=True)
    current_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    make: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    model_year: Mapped[int | None] = mapped_column(Integer)
    trim: Mapped[str | None] = mapped_column(String(80))
    vin: Mapped[str | None] = mapped_column(String(32))
    plate: Mapped[str | None] = mapped_column(String(32))
    plate_compact: Mapped[str | None] = mapped_column(String(32), index=True)
    engine_number: Mapped[str | None] = mapped_column(String(60))
    engine_type: Mapped[str | None] = mapped_column(String(60))
    fuel_type: Mapped[str | None] = mapped_column(String(30))
    engine_capacity: Mapped[str | None] = mapped_column(String(30))
    transmission: Mapped[str | None] = mapped_column(String(30))
    color: Mapped[str | None] = mapped_column(String(40))
    current_mileage: Mapped[int | None] = mapped_column(Integer)
    registration_country: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # VIN is optional but must be unique when present.
        Index("uq_vehicles_vin", "vin", unique=True, postgresql_where=text("vin IS NOT NULL")),
    )


class VehicleOwnership(Base):
    __tablename__ = "vehicle_ownerships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # at most one open ownership per vehicle
        Index("uq_open_ownership", "vehicle_id", unique=True, postgresql_where=text("end_at IS NULL")),
    )


class VehiclePlateHistory(Base):
    __tablename__ = "vehicle_plate_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True)
    plate: Mapped[str] = mapped_column(String(32))
    plate_compact: Mapped[str] = mapped_column(String(32), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VehicleVisit(Base):
    """One permanent record per workshop visit; customer_id is the owner at the time of the visit."""

    __tablename__ = "vehicle_visits"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_no: Mapped[int] = mapped_column(Integer, Identity(start=10000), unique=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    plate_at_visit: Mapped[str | None] = mapped_column(String(32))
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    mileage: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(50))
    complaint: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    actual_repairs: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="received")
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    expected_completion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __mapper_args__ = {"version_id_col": version}  # optimistic concurrency (StaleDataError -> 409)
    __table_args__ = (Index("ix_visits_vehicle_arrival", "vehicle_id", text("arrival_at DESC")),)
