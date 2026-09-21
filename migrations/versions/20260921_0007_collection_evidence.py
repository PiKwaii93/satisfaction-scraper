"""collection evidence and company metadata

Revision ID: 20260921_0007
Revises: 20260715_0006
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260921_0007"
down_revision = "20260715_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("domain", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("trustscore", sa.Float(), nullable=True))
    op.add_column("companies", sa.Column("total_review_count", sa.BigInteger(), nullable=True))
    op.add_column(
        "companies",
        sa.Column("rating_distribution", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("metadata_collected_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "analysis_runs",
        sa.Column(
            "collection_mode",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'sampled'"),
        ),
    )
    op.add_column("analysis_runs", sa.Column("max_pages", sa.Integer(), nullable=True))
    op.add_column("analysis_runs", sa.Column("pages_requested", sa.Integer(), nullable=True))
    op.add_column(
        "analysis_runs",
        sa.Column("pages_processed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("pages_succeeded", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("pages_failed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("reviews_extracted", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("unique_reviews", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("analysis_runs", sa.Column("stop_reason", sa.String(50), nullable=True))

    op.add_column("reviews", sa.Column("source_review_id", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("review_url", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("company_reply_text", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("reviews", "company_reply_text")
    op.drop_column("reviews", "review_url")
    op.drop_column("reviews", "source_review_id")
    op.drop_column("analysis_runs", "stop_reason")
    op.drop_column("analysis_runs", "unique_reviews")
    op.drop_column("analysis_runs", "reviews_extracted")
    op.drop_column("analysis_runs", "pages_failed")
    op.drop_column("analysis_runs", "pages_succeeded")
    op.drop_column("analysis_runs", "pages_processed")
    op.drop_column("analysis_runs", "pages_requested")
    op.drop_column("analysis_runs", "max_pages")
    op.drop_column("analysis_runs", "collection_mode")
    op.drop_column("companies", "metadata_collected_at")
    op.drop_column("companies", "rating_distribution")
    op.drop_column("companies", "total_review_count")
    op.drop_column("companies", "trustscore")
    op.drop_column("companies", "domain")
