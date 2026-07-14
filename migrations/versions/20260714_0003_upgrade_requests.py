"""Add upgrade request workflow.

Revision ID: 20260714_0003
Revises: 20260711_0002
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_0003"
down_revision = "20260711_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "upgrade_requests",
        sa.Column("upgrade_request_id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.organization_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_by_email", sa.String(length=255), nullable=True),
        sa.Column("current_plan", sa.String(length=40), nullable=False),
        sa.Column("requested_plan", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("handled_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_upgrade_requests_org_status",
        "upgrade_requests",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_upgrade_requests_open_plan",
        "upgrade_requests",
        ["organization_id", "requested_plan", "status"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'approved')"),
    )


def downgrade():
    op.drop_index("idx_upgrade_requests_open_plan", table_name="upgrade_requests")
    op.drop_index("idx_upgrade_requests_org_status", table_name="upgrade_requests")
    op.drop_table("upgrade_requests")
