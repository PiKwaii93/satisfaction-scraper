import json
import os
import psycopg2
from datetime import datetime, timedelta
import re
from app.sentiment_analysis import get_sentiment

def parse_relative_date(date_text):
    now = datetime.now()
    if not date_text or not isinstance(date_text, str):
        return now
    date_text = date_text.lower().strip()
    match = re.search(r'\d+', date_text)
    if not match:
        if "jour" in date_text: return now - timedelta(days=1)
        if "semaine" in date_text: return now - timedelta(weeks=1)
        if "heure" in date_text: return now - timedelta(hours=1)
        if "minute" in date_text: return now - timedelta(minutes=1)
        return now
    value = int(match.group())
    if "minute" in date_text: return now - timedelta(minutes=value)
    elif "heure" in date_text: return now - timedelta(hours=value)
    elif "jour" in date_text: return now - timedelta(days=value)
    elif "semaine" in date_text: return now - timedelta(weeks=value)
    return now

def run_etl(json_path=None):
    json_path = json_path or os.getenv("REVIEWS_JSON_PATH", "/app/data/showroom_reviews.json")
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

    cursor.execute("""
        INSERT INTO dim_companies (company_name, company_url, theme, total_reviews_count, trustscore)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (company_url) DO UPDATE 
        SET total_reviews_count = EXCLUDED.total_reviews_count
        RETURNING company_id;
    """, (data["target_company"], data["target_company"], "E-commerce", data["total_extracted"], 4.1))
    
    company_id = cursor.fetchone()[0]

    inserted_count = 0
    for review in data["reviews"]:
        raw_rating = str(review["rating"])
        nums = re.findall(r'\d+', raw_rating)
        rating_int = int(nums[0]) if nums else 3 
            
        verbatim_text = review["verbatim"].strip()

        # --- NOUVELLE STRATÉGIE : LE TEXTE FAIT FOI ---
        if not verbatim_text:
            # Cas 1 : Pas de texte -> Les étoiles restent la seule source d'info
            if rating_int <= 2: sentiment_label = 'Négatif'
            elif rating_int == 3: sentiment_label = 'Neutre'
            else: sentiment_label = 'Positif'
            sentiment_score = 1.0
        else:
            # Cas 2 : Il y a du texte -> L'IA décide seule (sans intervention des étoiles)
            sentiment_label, sentiment_score = get_sentiment(verbatim_text, rating_int)
            
            # Note : Nous avons supprimé le bloc "if sentiment_score < 0.55" 
            # pour que l'IA ne soit pas contrainte par la note utilisateur.

        # Insertion en base
        cursor.execute("""
            INSERT INTO fact_reviews (
                company_id, author_name, rating, review_date, verbatim, 
                company_responded, sentiment_label, sentiment_score
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (author_name, review_date, verbatim) DO NOTHING;
        """, (
            company_id, review["author"], rating_int, parse_relative_date(review["date"]), 
            verbatim_text, review["company_responded"], sentiment_label, sentiment_score
        ))
        
        if cursor.rowcount > 0:
            inserted_count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[+] ETL réussi : {inserted_count} avis traités. L'IA est désormais le seul juge.")

if __name__ == "__main__":
    run_etl()
