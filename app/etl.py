import json
import os
import psycopg2
from datetime import datetime, timedelta
import re
from app.sentiment_analysis import get_sentiment

def parse_relative_date(date_text):
    now = datetime.now()
    date_text = date_text.lower().strip()
    if "minute" in date_text:
        minutes = int(re.search(r'\d+', date_text).group())
        return now - timedelta(minutes=minutes)
    elif "heure" in date_text:
        hours = int(re.search(r'\d+', date_text).group()) if re.search(r'\d+', date_text) else 1
        return now - timedelta(hours=hours)
    elif "jour" in date_text:
        days = int(re.search(r'\d+', date_text).group()) if re.search(r'\d+', date_text) else 1
        return now - timedelta(days=days)
    elif "semaine" in date_text:
        weeks = int(re.search(r'\d+', date_text).group()) if re.search(r'\d+', date_text) else 1
        return now - timedelta(weeks=weeks)
    return now

def run_etl():
    json_path = "/app/data/showroom_reviews.json"
    if not os.path.exists(json_path):
        print("[-] Fichier JSON introuvable.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123")
    )
    cursor = conn.cursor()

    # 1. Insertion de l'entreprise (avec les champs complets)
    cursor.execute("""
        INSERT INTO dim_companies (company_name, company_url, theme, total_reviews_count, trustscore)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (company_url) DO UPDATE 
        SET total_reviews_count = EXCLUDED.total_reviews_count
        RETURNING company_id;
    """, (data["target_company"], data["target_company"], "E-commerce", data["total_extracted"], 4.1))
    
    company_id = cursor.fetchone()[0]

    # 2. Insertion des avis
    inserted_count = 0
    for review in data["reviews"]:
        try:
            rating_int = int(review["rating"]) if review["rating"].isdigit() else 3
        except:
            rating_int = 3
            
        verbatim_text = review["verbatim"]

        # --- LOGIQUE HYBRIDE NLP + RÈGLE MÉTIER ---
        sentiment_label, sentiment_score = get_sentiment(verbatim_text)
        
        if rating_int <= 2:
            sentiment_label, sentiment_score = "Négatif", -0.5
        elif rating_int >= 4:
            sentiment_label, sentiment_score = "Positif", 0.5

        # Insertion avec TOUTES les colonnes (dont company_responded)
        cursor.execute("""
            INSERT INTO fact_reviews (
                company_id, author_name, rating, review_date, verbatim, 
                company_responded, sentiment_label, sentiment_score
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            company_id, review["author"], rating_int, parse_relative_date(review["date"]), 
            verbatim_text, review["company_responded"], sentiment_label, sentiment_score
        ))
        inserted_count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[+] ETL réussi : {inserted_count} avis insérés avec hybridation.")

if __name__ == "__main__":
    run_etl()