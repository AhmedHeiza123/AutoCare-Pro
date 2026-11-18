"""Invoices keep a snapshot of the document settings (workshop letterhead, currency, payment-method names) taken at issue,
so a reprint years later looks like the original even if the workshop name/phone changed.

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("doc_snapshot", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "doc_snapshot")
