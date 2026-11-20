"""A user may hold more than one role (additive: no existing table or row is changed).

users.role_id stays the user's PRIMARY role (shown everywhere as before, so every existing user and client keeps working).
The new table user_roles holds the ADDITIONAL roles; a user's permissions are the union of all of his roles.

Revision ID: 0012
Revises: 0011
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_roles_role", "user_roles", ["role_id"])


def downgrade() -> None:
    """Drops only the additional roles; every user keeps his primary role."""
    op.drop_index("ix_user_roles_role", table_name="user_roles")
    op.drop_table("user_roles")
