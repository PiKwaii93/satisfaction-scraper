import json
import os
import time
from playwright.sync_api import sync_playwright

def scrape_trustpilot(company_slug, output_path, max_pages=1):
    base_url = f"https://fr.trustpilot.com/review/{company_slug}"
    print(f"[*] Démarrage du scraping Trustpilot pour : {company_slug}")
    
    reviews_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="fr-FR"
        )
        page = context.new_page()
        
        for current_page in range(1, max_pages + 1):
            url = f"{base_url}?page={current_page}"
            print(f"[*] Chargement de la page {current_page} : {url}")
            
            try:
                page.goto(url, wait_until="networkidle")
                time.sleep(2)
                
                # Gestion du bandeau de consentement des cookies
                cookie_button = page.query_selector("#onetrust-accept-btn-handler")
                if cookie_button and cookie_button.is_visible():
                    cookie_button.click()
                    time.sleep(1)

                # Extraction ciblée des conteneurs d'avis standard
                review_cards = page.query_selector_all("article[class*='styles_reviewCard']")
                
                if not review_cards:
                    print(f"[-] Aucun bloc d'avis trouvé sur la page {current_page}.")
                    break
                
                for card in review_cards:
                    try:
                        # 1. Extraction du Nom de l'auteur
                        author_elem = card.query_selector("[data-user-profile-link-name='title'], span[class*='styles_consumerName']")
                        author = author_elem.inner_text().strip() if author_elem else "Anonyme"
                        
                        # 2. Extraction de la Note (méthode robuste via l'attribut alt de l'image ou data-star-rating)
                        rating = "Non spécifié"
                        rating_container = card.query_selector("div[class*='styles_reviewHeader'] div[data-star-rating], div[class*='styles_reviewHeader'] img")
                        if rating_container:
                            # Tentative 1 : via l'attribut de note direct (ex: data-star-rating="5")
                            direct_rating = rating_container.get_attribute("data-star-rating")
                            if direct_rating:
                                rating = direct_rating
                            else:
                                # Tentative 2 : via le texte alternatif de l'image des étoiles
                                alt_text = rating_container.get_attribute("alt")
                                if alt_text and "Noté" in alt_text:
                                    rating = alt_text.split(" ")[1]
                        
                        # 3. Extraction de la Date
                        date_elem = card.query_selector("[data-submission-date-typography='true'], time")
                        date = date_elem.inner_text().strip() if date_elem else "Date inconnue"
                        if "Date de l'expérience" in date:
                            date = date.replace("Date de l'expérience :", "").strip()
                        
                        # 4. Extraction du Verbatim (Titre + Corps du commentaire)
                        title_elem = card.query_selector("[data-review-title-typography='true']")
                        body_elem = card.query_selector("[data-review-description-typography='true'], p[class*='typography_body-m']")
                        
                        title_text = title_elem.inner_text().strip() if title_elem else ""
                        body_text = body_elem.inner_text().strip() if body_elem else ""
                        
                        # On combine le titre et le texte pour un verbatim complet
                        verbatim = f"{title_text} - {body_text}".strip(" - ")
                        
                        # 5. Extraction de la Réponse Métier (Service Client)
                        company_reply = card.query_selector("[data-dashboard-reply-typography='true'], div[class*='styles_replyContainer']")
                        has_replied = True if company_reply else False
                        
                        # Filtrage pour éviter d'enregistrer des structures vides parasites
                        if verbatim or rating != "Non spécifié":
                            reviews_data.append({
                                "author": author,
                                "rating": rating,
                                "date": date,
                                "verbatim": verbatim,
                                "company_responded": has_replied
                            })
                        
                    except Exception as single_error:
                        continue
                        
            except Exception as page_error:
                print(f"[-] Erreur sur la page {current_page} : {page_error}")
                break
                
        browser.close()
        
    # --- SAUVEGARDE DE LA COLLECTE ---
    output_data = {
        "target_company": company_slug,
        "total_extracted": len(reviews_data),
        "reviews": reviews_data
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n[+] Succès : Fichier généré avec {len(reviews_data)} avis complets enrichis.")

if __name__ == "__main__":
    COMPANY = "www.showroomprive.com" 
    OUTPUT = "/app/data/showroom_reviews.json"
    scrape_trustpilot(company_slug=COMPANY, output_path=OUTPUT, max_pages=1)