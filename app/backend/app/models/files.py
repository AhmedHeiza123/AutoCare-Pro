import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Attachment(Base):
    """A photo or document linked to a record. Files are never deleted; removal is a soft, audited flag."""

    __tablename__ = "attachments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_type: Mapped[str] = mapped_column(String(20))  # visit | vehicle | part | quotation
    owner_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(10))  # photo | document
    point: Mapped[str | None] = mapped_column(String(50))  # e.g. front_bumper (inspection point)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(300))  # relative to the attachments folder; generated, never user input
    mime: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)
    removed_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_attachments_owner", "owner_type", "owner_id"),)
