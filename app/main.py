import time
import os
from scraper import scrape_trustpilot
from etl import run_etl

if __name__ == "__main__":
    COMPANY = "www.showroomprive.com" 
    OUTPUT = "/app/data/showroom_reviews.json"
    
    # On attend 5 secondes pour être sûr que PostgreSQL a fini de s'initialiser
    print("[*] Initialisation de l'environnement, attente du service BDD...")
    time.sleep(5) 
    
    # Étape 1 : Scraping (Extraction)
    scrape_trustpilot(company_slug=COMPANY, output_path=OUTPUT, max_pages=1)
    
    # Étape 2 : ETL (Transformation & Chargement)
    run_etl()