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