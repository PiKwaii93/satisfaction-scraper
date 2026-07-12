"""Add organization plan metadata.

Revision ID: 20260711_0002
Revises: 20260705_0001
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_0002"
down_revision = "20260705_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "organizations",
        sa.Column(
            "plan",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'business'"),
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("plan_updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_organizations_plan", "organizations", ["plan"])


def downgrade():
    op.drop_index("idx_organizations_plan", table_name="organizations")
    op.drop_column("organizations", "plan_updated_at")
    op.drop_column("organizations", "plan")
