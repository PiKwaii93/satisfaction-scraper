import json
import os
import time
import random
from playwright.sync_api import sync_playwright


def build_trustpilot_review_url(company_slug, star, current_page):
    base_url = f"https://fr.trustpilot.com/review/{company_slug}"
    if current_page == 1:
        return f"{base_url}?stars={star}"
    return f"{base_url}?page={current_page}&stars={star}"


def scrape_trustpilot_by_stars(company_slug, output_path, stars_list=[1, 2, 3], pages_per_star=2):
    """
    Scrape Trustpilot en filtrant par note (étoiles) pour équilibrer le dataset
    sans dépasser les pages critiques qui déclenchent les vérifications par email.
    """
    print(f"[*] Démarrage du scraping ciblé pour : {company_slug}")
    print(f"[*] Notes ciblées : {stars_list} ({pages_per_star} page(s) par note)")
    
    reviews_data = []
    seen_reviews = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="fr-FR"
        )
        page = context.new_page()
        
        # On boucle d'abord sur chaque note d'étoile configurée
        for star in stars_list:
            print(f"\n[+] Collecte des avis {star} étoile(s)...")
            
            for current_page in range(1, pages_per_star + 1):
                # Construction de l'URL filtrée dynamiquement
                url = build_trustpilot_review_url(company_slug, star, current_page)
                print(f"    [*] Page {current_page} : {url}")
                
                try:
                    page.goto(url, wait_until="networkidle")
                    
                    # Humanisation : délai aléatoire léger pour ne pas surcharger le serveur
                    time.sleep(random.uniform(2.0, 4.0))
                    
                    # Gestion unique du bandeau de cookies si visible
                    cookie_button = page.query_selector("#onetrust-accept-btn-handler")
                    if cookie_button and cookie_button.is_visible():
                        cookie_button.click()
                        time.sleep(1)

                    # Extraction des conteneurs d'avis
                    review_cards = page.query_selector_all("article[class*='styles_reviewCard']")
                    
                    if not review_cards:
                        print(f"    [-] Aucun bloc d'avis trouvé pour {star} étoile(s) à la page {current_page}.")
                        break
                    
                    for card in review_cards:
                        try:
                            # 1. Extraction du Nom de l'auteur
                            author_elem = card.query_selector("[data-user-profile-link-name='title'], span[class*='styles_consumerName']")
                            author = author_elem.inner_text().strip() if author_elem else "Anonyme"
                            
                            # 2. Extraction de la Note (Sécurité : si l'URL filtre mal, on valide la vraie note)
                            rating = str(star)
                            rating_container = card.query_selector("div[class*='styles_reviewHeader'] div[data-star-rating], div[class*='styles_reviewHeader'] img")
                            if rating_container:
                                direct_rating = rating_container.get_attribute("data-star-rating")
                                if direct_rating:
                                    rating = direct_rating
                                else:
                                    alt_text = rating_container.get_attribute("alt")
                                    if alt_text and "Noté" in alt_text:
                                        rating = alt_text.split(" ")[1]
                            
                            # 3. Extraction de la Date
                            date_elem = card.query_selector("[data-submission-date-typography='true'], time")
                            date = date_elem.inner_text().strip() if date_elem else "Date inconnue"
                            if "Date de l'expérience" in date:
                                date = date.replace("Date de l'expérience :", "").strip()
                            
                            # 4. Extraction et nettoyage du Verbatim (Titre + Corps)
                            title_elem = card.query_selector("[data-review-title-typography='true'], h2[data-service-review-title-typography='true']")
                            body_elem = card.query_selector("[data-service-review-text-typography='true'], p[class*='typography_body-m']")
                            
                            title_text = title_elem.inner_text().strip() if title_elem else ""
                            body_text = body_elem.inner_text().strip() if body_elem else ""
                            
                            if title_text.endswith("…") or title_text.endswith("..."):
                                verbatim = body_text if body_text else title_text
                            elif title_text.lower() in body_text.lower():
                                verbatim = body_text
                            else:
                                verbatim = f"{title_text} - {body_text}".strip(" - ")
                            
                            # 5. Extraction de la Réponse Métier
                            company_reply = card.query_selector("[data-dashboard-reply-typography='true'], div[class*='styles_replyContainer']")
                            has_replied = True if company_reply else False
                            
                            review_key = (
                                author.strip().lower(),
                                str(rating).strip(),
                                date.strip().lower(),
                                verbatim.strip().lower(),
                            )

                            if review_key in seen_reviews:
                                continue

                            if verbatim or rating != "Non spécifié":
                                seen_reviews.add(review_key)
                                reviews_data.append({
                                    "author": author,
                                    "rating": int(rating) if rating.isdigit() else rating,
                                    "date": date,
                                    "verbatim": verbatim,
                                    "company_responded": has_replied
                                })
                            
                        except Exception:
                            continue
                            
                except Exception as page_error:
                    print(f"    [-] Erreur lors du chargement de la page : {page_error}")
                    break
                    
        browser.close()
        
    # --- SAUVEGARDE DU DATASET ÉQUILIBRÉ ---
    output_data = {
        "target_company": company_slug,
        "total_extracted": len(reviews_data),
        "reviews": reviews_data
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n[+] Succès : Extraction terminée. Fichier généré avec {len(reviews_data)} avis.")

if __name__ == "__main__":
    COMPANY = "www.showroomprive.com" 
    OUTPUT = "/app/data/showroom_reviews.json"
    
    # Ici on cible explicitement les notes équilibrées (ex: 1, 2, 3, 4, 5) 
    # en restant uniquement sur les pages 1 et 2 pour chaque catégorie.
    scrape_trustpilot_by_stars(
        company_slug=COMPANY, 
        output_path=OUTPUT, 
        stars_list=[1, 2, 3, 4, 5], 
        pages_per_star=2
    )
