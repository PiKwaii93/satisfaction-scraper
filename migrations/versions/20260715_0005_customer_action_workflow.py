"""customer action workflow fields

Revision ID: 20260715_0005
Revises: 20260715_0004
Create Date: 2026-07-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0005"
down_revision = "20260715_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_actions", sa.Column("notes", sa.Text(), nullable=True))
    op.create_index(
        "idx_customer_actions_due_date",
        "customer_actions",
        ["organization_id", "due_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_customer_actions_due_date", table_name="customer_actions")
    op.drop_column("customer_actions", "notes")
