"""Create the product schema baseline.

Revision ID: 20260705_0001
Revises:
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260705_0001"
down_revision = None
branch_labels = None
depends_on = None

NOW = sa.text("NOW()")
EMPTY_JSON = sa.text("'{}'::jsonb")
PRODUCTION_MODEL = sa.text("'models:/sentiment_model@production'")


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column(
            "default_source",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'trustpilot'"),
        ),
        sa.Column(
            "default_pages_per_star",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.UniqueConstraint("slug", name="organizations_slug_key"),
    )

    op.create_table(
        "organization_review_sources",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_configured", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'not_configured'"),
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSON,
        ),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("organization_id", "source_id"),
    )
    op.create_index(
        "idx_org_review_sources_status",
        "organization_review_sources",
        ["organization_id", "status"],
    )

    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'member'"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "account_status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("invitation_token", sa.Text()),
        sa.Column("invitation_expires_at", sa.DateTime()),
        sa.Column("invited_at", sa.DateTime()),
        sa.Column("activated_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("email", name="users_email_key"),
        sa.UniqueConstraint("invitation_token", name="users_invitation_token_key"),
    )
    op.create_index("idx_users_org", "users", ["organization_id"])
    op.create_index(
        "idx_users_invitation_token",
        "users",
        ["invitation_token"],
        postgresql_where=sa.text("invitation_token IS NOT NULL"),
    )

    op.create_table(
        "companies",
        sa.Column("company_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("trustpilot_slug", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_companies_org_slug",
        "companies",
        ["organization_id", "trustpilot_slug"],
        unique=True,
    )

    op.create_table(
        "analysis_runs",
        sa.Column("run_id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer()),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'trustpilot'"),
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("stars_requested", sa.Text()),
        sa.Column(
            "pages_per_star", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("total_reviews", sa.Integer(), server_default=sa.text("0")),
        sa.Column("reviews_json_path", sa.Text()),
        sa.Column("predictions_csv_path", sa.Text()),
        sa.Column("celery_task_id", sa.Text()),
        sa.Column("model_uri", sa.Text(), server_default=PRODUCTION_MODEL),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.company_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("idx_analysis_runs_company", "analysis_runs", ["company_id"])
    op.create_index(
        "idx_analysis_runs_org", "analysis_runs", ["organization_id"]
    )

    op.create_table(
        "analysis_run_events",
        sa.Column("event_id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column(
            "level",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'info'"),
        ),
        sa.Column("step", sa.String(80)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_analysis_run_events_run", "analysis_run_events", ["run_id"]
    )

    op.create_table(
        "reviews",
        sa.Column("review_id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("external_review_key", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(150)),
        sa.Column("rating", sa.Integer()),
        sa.Column("raw_date", sa.Text()),
        sa.Column("review_date", sa.DateTime()),
        sa.Column("verbatim", sa.Text()),
        sa.Column(
            "company_responded", sa.Boolean(), server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.company_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "run_id",
            "external_review_key",
            name="reviews_run_id_external_review_key_key",
        ),
    )
    op.create_index("idx_reviews_run", "reviews", ["run_id"])
    op.create_index("idx_reviews_company", "reviews", ["company_id"])

    op.create_table(
        "sentiment_predictions",
        sa.Column("prediction_id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("model_uri", sa.Text(), server_default=PRODUCTION_MODEL),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.review_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("review_id", name="sentiment_predictions_review_id_key"),
    )
    op.create_index(
        "idx_predictions_label", "sentiment_predictions", ["label"]
    )

    op.create_table(
        "review_topics",
        sa.Column("review_topic_id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.review_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "review_id", "topic", name="review_topics_review_id_topic_key"
        ),
    )
    op.create_index("idx_review_topics_topic", "review_topics", ["topic"])

    op.create_table(
        "review_feedback",
        sa.Column("feedback_id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("predicted_label", sa.String(20), nullable=False),
        sa.Column("corrected_label", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.review_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("review_id", name="review_feedback_review_id_key"),
    )
    op.create_index(
        "idx_review_feedback_label", "review_feedback", ["corrected_label"]
    )

    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer()),
        sa.Column("actor_email", sa.String(255)),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80)),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSON,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
    )
    op.create_index(
        "idx_audit_events_org",
        "audit_events",
        ["organization_id", sa.text("audit_event_id DESC")],
    )
    op.create_index("idx_audit_events_type", "audit_events", ["event_type"])

    op.create_table(
        "business_alerts",
        sa.Column("alert_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer()),
        sa.Column("company_id", sa.Integer()),
        sa.Column("alert_type", sa.String(80), nullable=False),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'warning'"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=EMPTY_JSON,
        ),
        sa.Column("acknowledged_at", sa.DateTime()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.company_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_business_alerts_unique_run_type",
        "business_alerts",
        ["organization_id", "run_id", "alert_type"],
        unique=True,
    )
    op.create_index(
        "idx_business_alerts_org_status",
        "business_alerts",
        ["organization_id", "status", sa.text("alert_id DESC")],
    )
    op.create_index("idx_business_alerts_run", "business_alerts", ["run_id"])

    op.create_table(
        "model_training_runs",
        sa.Column("training_run_id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("celery_task_id", sa.Text()),
        sa.Column(
            "trigger_source",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'api'"),
        ),
        sa.Column("feedback_sample_weight", sa.Float()),
        sa.Column("training_rows", sa.Integer(), server_default=sa.text("0")),
        sa.Column("training_manual_rows", sa.Integer(), server_default=sa.text("0")),
        sa.Column("training_feedback_rows", sa.Integer(), server_default=sa.text("0")),
        sa.Column("training_effective_rows", sa.Float(), server_default=sa.text("0")),
        sa.Column("accuracy", sa.Float()),
        sa.Column("macro_f1", sa.Float()),
        sa.Column("weighted_f1", sa.Float()),
        sa.Column("model_version", sa.Text()),
        sa.Column("mlflow_run_id", sa.Text()),
        sa.Column("model_uri", sa.Text(), server_default=PRODUCTION_MODEL),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_model_training_runs_status", "model_training_runs", ["status"]
    )
    op.create_index(
        "idx_model_training_runs_org", "model_training_runs", ["organization_id"]
    )


def downgrade():
    op.drop_table("model_training_runs")
    op.drop_table("business_alerts")
    op.drop_table("audit_events")
    op.drop_table("review_feedback")
    op.drop_table("review_topics")
    op.drop_table("sentiment_predictions")
    op.drop_table("reviews")
    op.drop_table("analysis_run_events")
    op.drop_table("analysis_runs")
    op.drop_table("companies")
    op.drop_table("users")
    op.drop_table("organization_review_sources")
    op.drop_table("organizations")
