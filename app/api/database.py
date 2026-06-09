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
    CREATE TABLE IF NOT EXISTS companies (
        company_id SERIAL PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        trustpilot_slug VARCHAR(255) UNIQUE NOT NULL,
        source_url TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS analysis_runs (
        run_id SERIAL PRIMARY KEY,
        company_id INT REFERENCES companies(company_id) ON DELETE CASCADE,
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

    CREATE INDEX IF NOT EXISTS idx_analysis_runs_company
        ON analysis_runs(company_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_run
        ON reviews(run_id);
    CREATE INDEX IF NOT EXISTS idx_reviews_company
        ON reviews(company_id);
    CREATE INDEX IF NOT EXISTS idx_predictions_label
        ON sentiment_predictions(label);
    CREATE INDEX IF NOT EXISTS idx_review_topics_topic
        ON review_topics(topic);

    ALTER TABLE analysis_runs
        ADD COLUMN IF NOT EXISTS celery_task_id TEXT;
    """

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with get_cursor(commit=True) as cursor:
                cursor.execute(schema_sql)
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(delay_seconds)

    raise last_error
