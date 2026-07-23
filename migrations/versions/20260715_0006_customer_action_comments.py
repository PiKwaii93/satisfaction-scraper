"""customer action comments

Revision ID: 20260715_0006
Revises: 20260715_0005
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0006"
down_revision = "20260715_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_action_comments",
        sa.Column(
            "comment_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("action_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("author_user_id", sa.BigInteger(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["customer_actions.action_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.user_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index(
        "idx_customer_action_comments_action_created",
        "customer_action_comments",
        ["action_id", "created_at"],
    )
    op.create_index(
        "idx_customer_action_comments_org_created",
        "customer_action_comments",
        ["organization_id", "created_at"],
    )


def downgrade():
    op.drop_index(
        "idx_customer_action_comments_org_created",
        table_name="customer_action_comments",
    )
    op.drop_index(
        "idx_customer_action_comments_action_created",
        table_name="customer_action_comments",
    )
    op.drop_table("customer_action_comments")
