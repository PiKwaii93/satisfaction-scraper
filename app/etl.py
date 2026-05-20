import json
import os
import psycopg2
from datetime import datetime, timedelta
import re

def parse_relative_date(date_text):
    """
    Convertit les dates relatives de Trustpilot (ex: 'Il y a 33 minutes', 'Il y a un jour')
    en un objet datetime absolu.
    """
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
    elif "mois" in date_text:
        months = int(re.search(r'\d+', date_text).group()) if re.search(r'\d+', date_text) else 1
        return now - timedelta(days=months * 30)
    else:
        # Si c'est déjà une date fixe (ex: "10 mai 2026")
        # Pour simplifier dans un premier temps, on met la date du jour si le parsing échoue
        return now

def run_etl():
    json_path = "/app/data/showroom_reviews.json"
    if not os.path.exists(json_path):
        print(f"[-] Fichier JSON introuvable à l'emplacement : {json_path}")
        return

    print("[*] Lancement du pipeline ETL...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    company_url = data["target_company"]
    company_name = company_url.split(".")[1].capitalize() # Génère "Showroomprive"

    # Connexion à PostgreSQL (en utilisant les variables d'environnement de Docker Compose)
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123")
    )
    cursor = conn.cursor()

    try:
        # 1. Insertion ou récupération de l'entreprise dans dim_companies
        cursor.execute("""
            INSERT INTO dim_companies (company_name, company_url, theme, total_reviews_count, trustscore)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_url) DO UPDATE 
            SET total_reviews_count = EXCLUDED.total_reviews_count
            RETURNING company_id;
        """, (company_name, company_url, "E-commerce", data["total_extracted"], 4.1))
        
        company_id = cursor.fetchone()[0]

        # 2. Insertion des avis dans fact_reviews
        inserted_count = 0
        for review in data["reviews"]:
            # Nettoyage de la note (conversion en entier)
            try:
                rating_int = int(review["rating"])
            except ValueError:
                rating_int = None

            # Conversion de la date
            parsed_date = parse_relative_date(review["date"])

            cursor.execute("""
                INSERT INTO fact_reviews (company_id, author_name, rating, review_date, verbatim, company_responded)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (company_id, review["author"], rating_int, parsed_date, review["verbatim"], review["company_responded"]))
            inserted_count += 1

        conn.commit()
        print(f"[+] ETL réussi : {inserted_count} avis insérés en base de données pour {company_name}.")

    except Exception as e:
        conn.rollback()
        print(f"[-] Erreur lors de l'ETL : {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_etl()