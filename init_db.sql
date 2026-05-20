-- Création de la table des entreprises (Dimensions)
CREATE TABLE IF NOT EXISTS dim_companies (
    company_id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    company_url VARCHAR(255) UNIQUE NOT NULL,
    theme VARCHAR(100),
    total_reviews_count INT,
    trustscore FLOAT,
    pct_excellent_reviews FLOAT
);

-- Création de la table des avis (Faits)
CREATE TABLE IF NOT EXISTS fact_reviews (
    review_id SERIAL PRIMARY KEY,
    company_id INT REFERENCES dim_companies(company_id) ON DELETE CASCADE,
    author_name VARCHAR(150),
    rating INT,
    review_date TIMESTAMP,
    verbatim TEXT,
    company_responded BOOLEAN DEFAULT FALSE
);

-- Index pour accélérer les futures requêtes de Text Mining
CREATE INDEX IF NOT EXISTS idx_verbatim ON fact_reviews(verbatim);