import os
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from psycopg2 import OperationalError as PsycopgOperationalError
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError as SqlAlchemyOperationalError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"
SCHEMA_MIGRATION_LOCK_ID = 724_110_2026

PRODUCT_SCHEMA_REQUIREMENTS = {
    "organizations": {
        "organization_id",
        "name",
        "slug",
        "plan",
        "plan_updated_at",
        "default_source",
        "default_pages_per_star",
        "created_at",
        "updated_at",
    },
    "organization_review_sources": {
        "organization_id",
        "source_id",
        "is_enabled",
        "is_configured",
        "status",
        "config",
        "last_error",
        "created_at",
        "updated_at",
    },
    "users": {
        "user_id",
        "organization_id",
        "email",
        "full_name",
        "password_hash",
        "role",
        "is_active",
        "account_status",
        "invitation_token",
        "invitation_expires_at",
        "invited_at",
        "activated_at",
        "created_at",
        "updated_at",
    },
    "companies": {
        "company_id",
        "organization_id",
        "company_name",
        "trustpilot_slug",
        "source_url",
        "created_at",
        "updated_at",
    },
    "analysis_runs": {
        "run_id",
        "company_id",
        "organization_id",
        "source",
        "status",
        "stars_requested",
        "pages_per_star",
        "total_reviews",
        "reviews_json_path",
        "predictions_csv_path",
        "celery_task_id",
        "model_uri",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    },
    "analysis_run_events": {
        "event_id",
        "run_id",
        "level",
        "step",
        "message",
        "created_at",
    },
    "reviews": {
        "review_id",
        "run_id",
        "company_id",
        "external_review_key",
        "author_name",
        "rating",
        "raw_date",
        "review_date",
        "verbatim",
        "company_responded",
        "created_at",
    },
    "sentiment_predictions": {
        "prediction_id",
        "review_id",
        "label",
        "score",
        "model_uri",
        "created_at",
    },
    "review_topics": {
        "review_topic_id",
        "review_id",
        "topic",
        "created_at",
    },
    "review_feedback": {
        "feedback_id",
        "review_id",
        "predicted_label",
        "corrected_label",
        "comment",
        "created_at",
        "updated_at",
    },
    "audit_events": {
        "audit_event_id",
        "organization_id",
        "user_id",
        "actor_email",
        "event_type",
        "entity_type",
        "entity_id",
        "summary",
        "metadata",
        "created_at",
    },
    "business_alerts": {
        "alert_id",
        "organization_id",
        "run_id",
        "company_id",
        "alert_type",
        "severity",
        "title",
        "message",
        "status",
        "metadata",
        "acknowledged_at",
        "resolved_at",
        "created_at",
        "updated_at",
    },
    "customer_actions": {
        "action_id",
        "organization_id",
        "alert_id",
        "run_id",
        "title",
        "description",
        "priority",
        "status",
        "owner_name",
        "due_date",
        "notes",
        "created_by_user_id",
        "updated_by_user_id",
        "created_at",
        "updated_at",
        "resolved_at",
    },
    "upgrade_requests": {
        "upgrade_request_id",
        "organization_id",
        "requested_by_user_id",
        "requested_by_email",
        "current_plan",
        "requested_plan",
        "status",
        "source",
        "note",
        "metadata",
        "created_at",
        "updated_at",
        "handled_at",
    },
    "model_training_runs": {
        "training_run_id",
        "organization_id",
        "status",
        "celery_task_id",
        "trigger_source",
        "feedback_sample_weight",
        "training_rows",
        "training_manual_rows",
        "training_feedback_rows",
        "training_effective_rows",
        "accuracy",
        "macro_f1",
        "weighted_f1",
        "model_version",
        "mlflow_run_id",
        "model_uri",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    },
}

PRODUCT_INDEX_REQUIREMENTS = {
    "organization_review_sources": {"idx_org_review_sources_status"},
    "users": {"idx_users_org", "idx_users_invitation_token"},
    "companies": {"idx_companies_org_slug"},
    "analysis_runs": {"idx_analysis_runs_company", "idx_analysis_runs_org"},
    "analysis_run_events": {"idx_analysis_run_events_run"},
    "reviews": {"idx_reviews_run", "idx_reviews_company"},
    "sentiment_predictions": {"idx_predictions_label"},
    "review_topics": {"idx_review_topics_topic"},
    "review_feedback": {"idx_review_feedback_label"},
    "audit_events": {"idx_audit_events_org", "idx_audit_events_type"},
    "business_alerts": {
        "idx_business_alerts_unique_run_type",
        "idx_business_alerts_org_status",
        "idx_business_alerts_run",
    },
    "customer_actions": {
        "idx_customer_actions_alert",
        "idx_customer_actions_due_date",
        "idx_customer_actions_org_status",
        "idx_customer_actions_run",
        "idx_customer_actions_unique_alert",
    },
    "upgrade_requests": {
        "idx_upgrade_requests_org_status",
        "idx_upgrade_requests_open_plan",
    },
    "model_training_runs": {
        "idx_model_training_runs_status",
        "idx_model_training_runs_org",
    },
}


class SchemaMigrationError(RuntimeError):
    """Raised when an unversioned database cannot be baselined safely."""


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "postgres_db"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "satisfaction_client"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASSWORD", "password123"),
    }


def get_database_url():
    config = get_db_config()
    return URL.create(
        drivername="postgresql+psycopg2",
        username=config["user"],
        password=config["password"],
        host=config["host"],
        port=config["port"],
        database=config["database"],
    )


@contextmanager
def get_connection():
    conn = psycopg2.connect(**get_db_config())
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(commit=False):
    with get_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def get_alembic_config(connection=None):
    config = Config(str(ALEMBIC_CONFIG_PATH))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def _validate_existing_product_schema(connection):
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    expected_tables = set(PRODUCT_SCHEMA_REQUIREMENTS)
    present_tables = table_names & expected_tables

    if not present_tables:
        return "empty"

    missing_tables = sorted(expected_tables - present_tables)
    if missing_tables:
        raise SchemaMigrationError(
            "Schema produit partiel: tables manquantes avant baseline Alembic: "
            + ", ".join(missing_tables)
        )

    errors = []
    for table_name, required_columns in PRODUCT_SCHEMA_REQUIREMENTS.items():
        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        missing_columns = sorted(required_columns - existing_columns)
        if missing_columns:
            errors.append(f"{table_name}: colonnes {', '.join(missing_columns)}")

    for table_name, required_indexes in PRODUCT_INDEX_REQUIREMENTS.items():
        existing_indexes = {
            index["name"] for index in inspector.get_indexes(table_name)
        }
        missing_indexes = sorted(required_indexes - existing_indexes)
        if missing_indexes:
            errors.append(f"{table_name}: index {', '.join(missing_indexes)}")

    if errors:
        raise SchemaMigrationError(
            "Schema produit incompatible avec la baseline Alembic: " + "; ".join(errors)
        )

    return "existing"


def _run_upgrade_on_connection(connection):
    config = get_alembic_config(connection)
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    migration_context = MigrationContext.configure(connection)
    current_heads = migration_context.get_current_heads()

    if "alembic_version" not in table_names or not current_heads:
        schema_state = _validate_existing_product_schema(connection)
        if schema_state == "existing":
            command.stamp(config, "head")
            return "stamped"

    command.upgrade(config, "head")
    return "upgraded"


def run_schema_migrations():
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": SCHEMA_MIGRATION_LOCK_ID},
            )
            return _run_upgrade_on_connection(connection)
    finally:
        engine.dispose()


def run_schema_downgrade(revision="-1"):
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": SCHEMA_MIGRATION_LOCK_ID},
            )
            command.downgrade(get_alembic_config(connection), revision)
    finally:
        engine.dispose()


def get_schema_revision():
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current = context.get_current_revision()
            head = ScriptDirectory.from_config(get_alembic_config()).get_current_head()
            return {"current": current, "head": head}
    finally:
        engine.dispose()


def ensure_product_schema(max_attempts=1, delay_seconds=1):
    """Upgrade or safely baseline the product schema, then seed the demo identity."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            run_schema_migrations()
            from app.api.auth import seed_demo_identity
            from app.api.services.review_sources import (
                ensure_organization_source_rows,
            )

            seed_demo_identity()
            with get_cursor() as cursor:
                cursor.execute("SELECT organization_id FROM organizations;")
                organization_ids = [
                    row["organization_id"] for row in cursor.fetchall()
                ]
            for organization_id in organization_ids:
                ensure_organization_source_rows(organization_id)
            return
        except (PsycopgOperationalError, SqlAlchemyOperationalError) as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(delay_seconds)

    raise last_error
