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

CREATE INDEX IF NOT EXISTS idx_analysis_runs_company ON analysis_runs(company_id);
CREATE INDEX IF NOT EXISTS idx_analysis_run_events_run ON analysis_run_events(run_id);
CREATE INDEX IF NOT EXISTS idx_reviews_run ON reviews(run_id);
CREATE INDEX IF NOT EXISTS idx_reviews_company ON reviews(company_id);
CREATE INDEX IF NOT EXISTS idx_predictions_label ON sentiment_predictions(label);
CREATE INDEX IF NOT EXISTS idx_review_topics_topic ON review_topics(topic);
