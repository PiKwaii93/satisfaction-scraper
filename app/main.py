import time
import os
# MODIFICATION : On importe la nouvelle fonction adaptée aux filtres d'étoiles
from scraper import scrape_trustpilot_by_stars
from etl import run_etl

def parse_stars(value):
    return [int(star.strip()) for star in value.split(",") if star.strip()]

if __name__ == "__main__":
    COMPANY = os.getenv("TRUSTPILOT_COMPANY", "www.showroomprive.com")
    OUTPUT = os.getenv("REVIEWS_JSON_PATH", "/app/data/showroom_reviews.json")
    STARS = parse_stars(os.getenv("TRUSTPILOT_STARS", "1,2,3,4,5"))
    PAGES_PER_STAR = int(os.getenv("PAGES_PER_STAR", "10"))
    
    # On attend 5 secondes pour être sûr que PostgreSQL a fini de s'initialiser
    print("[*] Initialisation de l'environnement, attente du service BDD...")
    time.sleep(5) 
    
    # Étape 1 : Scraping (Extraction) - MODIFICATION : Stratégie par étoiles pour éviter le blocage
    # On cible les pages 1 et 2 pour chaque note (1 à 5 étoiles) soit 10 pages explorées au total de façon sécurisée
    scrape_trustpilot_by_stars(
        company_slug=COMPANY, 
        output_path=OUTPUT, 
        stars_list=STARS,
        pages_per_star=PAGES_PER_STAR
    )
    
    # Étape 2 : ETL (Transformation & Chargement)
    run_etl(OUTPUT)
