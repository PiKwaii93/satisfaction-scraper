-- Suppression des tables existantes pour repartir sur une base propre à chaque build
DROP TABLE IF EXISTS fact_reviews CASCADE;
DROP TABLE IF EXISTS dim_companies CASCADE;

-- Création de la table des entreprises (Dimensions)
CREATE TABLE dim_companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    company_url VARCHAR(255) UNIQUE NOT NULL,
    theme VARCHAR(100),
    total_reviews_count INT,
    trustscore FLOAT,
    pct_excellent_reviews FLOAT
);

-- Création de la table des avis (Faits) incluant les colonnes NLP
CREATE TABLE fact_reviews (
    review_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES dim_companies(company_id) ON DELETE CASCADE,
    author_name VARCHAR(150),
    rating INT,
    review_date TIMESTAMP,
    verbatim TEXT,
    company_responded BOOLEAN DEFAULT FALSE,
    -- Ajouts pour l'étape NLP :
    sentiment_label VARCHAR(20),
    sentiment_score FLOAT
);

-- Index pour accélérer les futures requêtes de Text Mining
CREATE INDEX idx_verbatim ON fact_reviews(verbatim);

-- Tables produit pour l'application client historisee
CREATE TABLE IF NOT EXISTS organizations (
    organization_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    default_source VARCHAR(50) NOT NULL DEFAULT 'trustpilot',
    default_pages_per_star INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

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

INSERT INTO organizations (name, slug, updated_at)
VALUES ('Demo Satisfaction Client', 'demo', NOW())
ON CONFLICT (slug) DO UPDATE
SET updated_at = NOW();

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

CREATE TABLE IF NOT EXISTS companies (
    company_id SERIAL PRIMARY KEY,
    organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE
        DEFAULT 1,
    company_name VARCHAR(255) NOT NULL,
    trustpilot_slug VARCHAR(255) NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (organization_id, trustpilot_slug)
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES companies(company_id) ON DELETE CASCADE,
    organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE
        DEFAULT 1,
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
    organization_id INT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE
        DEFAULT 1,
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

CREATE INDEX IF NOT EXISTS idx_analysis_runs_company ON analysis_runs(company_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_org ON analysis_runs(organization_id);
CREATE INDEX IF NOT EXISTS idx_analysis_run_events_run ON analysis_run_events(run_id);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_invitation_token ON users(invitation_token)
    WHERE invitation_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_org_review_sources_status
    ON organization_review_sources(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_reviews_run ON reviews(run_id);
CREATE INDEX IF NOT EXISTS idx_reviews_company ON reviews(company_id);
CREATE INDEX IF NOT EXISTS idx_predictions_label ON sentiment_predictions(label);
CREATE INDEX IF NOT EXISTS idx_review_topics_topic ON review_topics(topic);
CREATE INDEX IF NOT EXISTS idx_review_feedback_label ON review_feedback(corrected_label);
CREATE INDEX IF NOT EXISTS idx_audit_events_org ON audit_events(organization_id, audit_event_id DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_business_alerts_unique_run_type
    ON business_alerts(organization_id, run_id, alert_type);
CREATE INDEX IF NOT EXISTS idx_business_alerts_org_status
    ON business_alerts(organization_id, status, alert_id DESC);
CREATE INDEX IF NOT EXISTS idx_business_alerts_run ON business_alerts(run_id);
CREATE INDEX IF NOT EXISTS idx_model_training_runs_status ON model_training_runs(status);
CREATE INDEX IF NOT EXISTS idx_model_training_runs_org ON model_training_runs(organization_id);
