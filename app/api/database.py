import os
import time
from contextlib import contextmanager

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor


def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "postgres_db"),
        "database": os.getenv("DB_NAME", "satisfaction_client"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASSWORD", "password123"),
    }


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


def ensure_product_schema(max_attempts=1, delay_seconds=1):
    """Create the product tables used by the FastAPI app if they do not exist."""
    schema_sql = """
    CREATE TABLE IF NOT EXISTS organizations (
        organization_id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(255) UNIQUE NOT NULL,
        default_source VARCHAR(50) NOT NULL DEFAULT 'trustpilot',
        default_pages_per_star INT NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS default_source VARCHAR(50) NOT NULL DEFAULT 'trustpilot';
    ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS default_pages_per_star INT NOT NULL DEFAULT 1;

    CREATE TABLE IF NOT EXISTS organization_review_sources (
        organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
        source_id VARCHAR(80) NOT NULL,
        is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        is_configured BOOLEAN NOT NULL DEFAULT FALSE,
        status VARCHAR(30) NOT NULL DEFAULT 'not_configured',
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        last_error TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (organization_id, source_id)
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
        email VARCHAR(255) UNIQUE NOT NULL,
        full_name VARCHAR(255),
        password_hash TEXT NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'member',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        account_status VARCHAR(30) NOT NULL DEFAULT 'active',
        invitation_token TEXT UNIQUE,
        invitation_expires_at TIMESTAMP,
        invited_at TIMESTAMP,
        activated_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS account_status VARCHAR(30) NOT NULL DEFAULT 'active';
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS invitation_token TEXT UNIQUE;
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS invitation_expires_at TIMESTAMP;
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS invited_at TIMESTAMP;
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP;

    UPDATE users
    SET account_status = CASE WHEN is_active THEN 'active' ELSE 'pending' END
    WHERE account_status IS NULL;

    UPDATE users
    SET activated_at = COALESCE(activated_at, created_at)
    WHERE is_active = TRUE;

    CREATE TABLE IF NOT EXISTS companies (
        company_id SERIAL PRIMARY KEY,
        organization_id INT REFERENCES organizations(organization_id) ON DELETE CASCADE,
        company_name VARCHAR(255) NOT NULL,
        trustpilot_slug VARCHAR(255) NOT NULL,
        source_url TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS analysis_runs (
        run_id SERIAL PRIMARY KEY,
        company_id INT REFERENCES companies(company_id) ON DELETE CASCADE,
        organization_id INT REFERENCES organizations(organization_id) ON DELETE CASCADE,
        source VARCHAR(50) NOT NULL DEFAULT 'trustpilot',
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        stars_requested TEXT,
        pages_per_star INT NOT NULL DEFAULT 1,
        total_reviews INT DEFAULT 0,
        reviews_json_path TEXT,
        predictions_csv_path TEXT,
        celery_task_id TEXT,
        model_uri TEXT DEFAULT 'models:/sentiment_model@production',
        error_message TEXT,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS analysis_run_events (
        event_id SERIAL PRIMARY KEY,
        run_id INT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
        level VARCHAR(20) NOT NULL DEFAULT 'info',
        step VARCHAR(80),
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS reviews (
        review_id SERIAL PRIMARY KEY,
        run_id INT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
        company_id INT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
        external_review_key TEXT NOT NULL,
        author_name VARCHAR(150),
        rating INT,
        raw_date TEXT,
        review_date TIMESTAMP,
        verbatim TEXT,
        company_responded BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (run_id, external_review_key)
    );

    CREATE TABLE IF NOT EXISTS sentiment_predictions (
        prediction_id SERIAL PRIMARY KEY,
        review_id INT NOT NULL UNIQUE REFERENCES reviews(review_id) ON DELETE CASCADE,
        label VARCHAR(20) NOT NULL,
        score FLOAT NOT NULL,
        model_uri TEXT DEFAULT 'models:/sentiment_model@production',
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS review_topics (
        review_topic_id SERIAL PRIMARY KEY,
        review_id INT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
        topic VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (review_id, topic)
    );

    CREATE TABLE IF NOT EXISTS review_feedback (
        feedback_id SERIAL PRIMARY KEY,
        review_id INT NOT NULL UNIQUE REFERENCES reviews(review_id) ON DELETE CASCADE,
        predicted_label VARCHAR(20) NOT NULL,
        corrected_label VARCHAR(20) NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS audit_events (
        audit_event_id SERIAL PRIMARY KEY,
        organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
        user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
        actor_email VARCHAR(255),
        event_type VARCHAR(80) NOT NULL,
        entity_type VARCHAR(80),
        entity_id INT,
        summary TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS business_alerts (
        alert_id SERIAL PRIMARY KEY,
        organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
        run_id INT REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
        company_id INT REFERENCES companies(company_id) ON DELETE SET NULL,
        alert_type VARCHAR(80) NOT NULL,
        severity VARCHAR(20) NOT NULL DEFAULT 'warning',
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'open',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        acknowledged_at TIMESTAMP,
        resolved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS model_training_runs (
        training_run_id SERIAL PRIMARY KEY,
        organization_id INT REFERENCES organizations(organization_id) ON DELETE CASCADE,
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        celery_task_id TEXT,
        trigger_source VARCHAR(50) NOT NULL DEFAULT 'api',
        feedback_sample_weight FLOAT,
        training_rows INT DEFAULT 0,
        training_manual_rows INT DEFAULT 0,
        training_feedback_rows INT DEFAULT 0,
        training_effective_rows FLOAT DEFAULT 0,
        accuracy FLOAT,
        macro_f1 FLOAT,
        weighted_f1 FLOAT,
        model_version TEXT,
        mlflow_run_id TEXT,
        model_uri TEXT DEFAULT 'models:/sentiment_model@production',
        error_message TEXT,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS organization_id INT;
    ALTER TABLE analysis_runs
        ADD COLUMN IF NOT EXISTS organization_id INT;
    ALTER TABLE model_training_runs
        ADD COLUMN IF NOT EXISTS organization_id INT;

    INSERT INTO organizations (name, slug, updated_at)
    VALUES ('Demo Satisfaction Client', 'demo', NOW())
    ON CONFLICT (slug) DO UPDATE
    SET updated_at = NOW();

    UPDATE companies
    SET organization_id = (SELECT organization_id FROM organizations WHERE slug = 'demo')
    WHERE organization_id IS NULL;
    UPDATE analysis_runs ar
    SET organization_id = c.organization_id
    FROM companies c
    WHERE ar.company_id = c.company_id
      AND ar.organization_id IS NULL;
    UPDATE model_training_runs
    SET organization_id = (SELECT organization_id FROM organizations WHERE slug = 'demo')
    WHERE organization_id IS NULL;

    INSERT INTO organization_review_sources (
        organization_id,
        source_id,
        is_enabled,
        is_configured,
        status
    )
    SELECT organization_id, 'trustpilot', TRUE, TRUE, 'active'
    FROM organizations
    ON CONFLICT (organization_id, source_id) DO NOTHING;

    INSERT INTO organization_review_sources (
        organization_id,
        source_id,
        is_enabled,
        is_configured,
        status
    )
    SELECT organization_id, 'csv', TRUE, TRUE, 'active'
    FROM organizations
    ON CONFLICT (organization_id, source_id) DO NOTHING;

    INSERT INTO organization_review_sources (
        organization_id,
        source_id,
        is_enabled,
        is_configured,
        status
    )
    SELECT organization_id, source_id, FALSE, FALSE, 'planned'
    FROM organizations
    CROSS JOIN (
        VALUES
            ('google_reviews'),
            ('zendesk'),
            ('shopify'),
            ('internal_support')
    ) AS planned_sources(source_id)
    ON CONFLICT (organization_id, source_id) DO NOTHING;

    ALTER TABLE companies
        ALTER COLUMN organization_id SET NOT NULL;
    ALTER TABLE analysis_runs
        ALTER COLUMN organization_id SET NOT NULL;
    ALTER TABLE model_training_runs
        ALTER COLUMN organization_id SET NOT NULL;

    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'companies_trustpilot_slug_key'
        ) THEN
            ALTER TABLE companies DROP CONSTRAINT companies_trustpilot_slug_key;
        END IF;
    END
    $$;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_org_slug
        ON companies(organization_id, trustpilot_slug);
    CREATE INDEX IF NOT EXISTS idx_users_org
        ON users(organization_id);
    CREATE INDEX IF NOT EXISTS idx_users_invitation_token
        ON users(invitation_token)
        WHERE invitation_token IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_org_review_sources_status
        ON organization_review_sources(organization_id, status);
    CREATE INDEX IF NOT EXISTS idx_analysis_runs_company
        ON analysis_runs(company_id);
    CREATE INDEX IF NOT EXISTS idx_analysis_runs_org
        ON analysis_runs(organization_id);
    CREATE INDEX IF NOT EXISTS idx_analysis_run_events_run
        ON analysis_run_events(run_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_run
        ON reviews(run_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_company
        ON reviews(company_id);
    CREATE INDEX IF NOT EXISTS idx_predictions_label
        ON sentiment_predictions(label);
    CREATE INDEX IF NOT EXISTS idx_review_topics_topic
        ON review_topics(topic);
    CREATE INDEX IF NOT EXISTS idx_review_feedback_label
        ON review_feedback(corrected_label);
    CREATE INDEX IF NOT EXISTS idx_audit_events_org
        ON audit_events(organization_id, audit_event_id DESC);
    CREATE INDEX IF NOT EXISTS idx_audit_events_type
        ON audit_events(event_type);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_business_alerts_unique_run_type
        ON business_alerts(organization_id, run_id, alert_type);
    CREATE INDEX IF NOT EXISTS idx_business_alerts_org_status
        ON business_alerts(organization_id, status, alert_id DESC);
    CREATE INDEX IF NOT EXISTS idx_business_alerts_run
        ON business_alerts(run_id);
    CREATE INDEX IF NOT EXISTS idx_model_training_runs_status
        ON model_training_runs(status);
    CREATE INDEX IF NOT EXISTS idx_model_training_runs_org
        ON model_training_runs(organization_id);

    ALTER TABLE analysis_runs
        ADD COLUMN IF NOT EXISTS celery_task_id TEXT;
    """

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with get_cursor(commit=True) as cursor:
                cursor.execute(schema_sql)
            from app.api.auth import seed_demo_identity

            seed_demo_identity()
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(delay_seconds)

    raise last_error
