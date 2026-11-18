"""Allow deleting an invoice that is still a draft (never issued). Issued/cancelled invoices stay undeletable.

Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

BODY = """
    CREATE OR REPLACE FUNCTION invoices_guard() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            IF {allow_draft} THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'invoices cannot be deleted';
        END IF;
        IF OLD.status <> 'draft' AND (
            NEW.subtotal, NEW.discount, NEW.tax_rate, NEW.tax_amount, NEW.total, NEW.customer_id,
            NEW.visit_id, NEW.vehicle_id, NEW.invoice_no, NEW.currency
        ) IS DISTINCT FROM (
            OLD.subtotal, OLD.discount, OLD.tax_rate, OLD.tax_amount, OLD.total, OLD.customer_id,
            OLD.visit_id, OLD.vehicle_id, OLD.invoice_no, OLD.currency
        ) THEN
            RAISE EXCEPTION 'finalized invoices are immutable';
        END IF;
        IF OLD.status = 'cancelled' AND NEW.status <> 'cancelled' THEN
            RAISE EXCEPTION 'cancelled invoices cannot be reopened';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute(BODY.format(allow_draft="OLD.status = 'draft'"))


def downgrade() -> None:
    op.execute(BODY.format(allow_draft="FALSE"))
