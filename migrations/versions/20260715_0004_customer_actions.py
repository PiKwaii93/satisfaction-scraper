"""Add customer action tracking.

Revision ID: 20260715_0004
Revises: 20260714_0003
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0004"
down_revision = "20260714_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_actions",
        sa.Column("action_id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.organization_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("business_alerts.alert_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("analysis_runs.run_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            sa.String(length=40),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default="open",
        ),
        sa.Column("owner_name", sa.String(length=160), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_customer_actions_priority",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'ignored')",
            name="ck_customer_actions_status",
        ),
    )
    op.create_index(
        "idx_customer_actions_org_status",
        "customer_actions",
        ["organization_id", "status"],
    )
    op.create_index("idx_customer_actions_run", "customer_actions", ["run_id"])
    op.create_index("idx_customer_actions_alert", "customer_actions", ["alert_id"])
    op.create_index(
        "idx_customer_actions_unique_alert",
        "customer_actions",
        ["organization_id", "alert_id"],
        unique=True,
        postgresql_where=sa.text("alert_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("idx_customer_actions_unique_alert", table_name="customer_actions")
    op.drop_index("idx_customer_actions_alert", table_name="customer_actions")
    op.drop_index("idx_customer_actions_run", table_name="customer_actions")
    op.drop_index("idx_customer_actions_org_status", table_name="customer_actions")
    op.drop_table("customer_actions")
