-- Historical tables kept for compatibility with the original data pipeline.
-- Product tables are created and versioned by Alembic when the API starts.

DROP TABLE IF EXISTS fact_reviews CASCADE;
DROP TABLE IF EXISTS dim_companies CASCADE;

CREATE TABLE dim_companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    company_url VARCHAR(255) UNIQUE NOT NULL,
    theme VARCHAR(100),
    total_reviews_count INT,
    trustscore FLOAT,
    pct_excellent_reviews FLOAT
);

CREATE TABLE fact_reviews (
    review_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES dim_companies(company_id) ON DELETE CASCADE,
    author_name VARCHAR(150),
    rating INT,
    review_date TIMESTAMP,
    verbatim TEXT,
    company_responded BOOLEAN DEFAULT FALSE,
    sentiment_label VARCHAR(20),
    sentiment_score FLOAT
);

CREATE INDEX idx_verbatim ON fact_reviews(verbatim);
