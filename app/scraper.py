import json
import os
import random
import re
import time
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


SAMPLED_MODE = "sampled"
REPRESENTATIVE_MODE = "representative"
STOP_NATURAL_END = "natural_end"
STOP_USER_LIMIT = "user_limit"
STOP_ERROR = "error"
STOP_PLATFORM_LIMITATION = "platform_limitation"


def build_trustpilot_review_url(company_slug, star, current_page):
    base_url = f"https://fr.trustpilot.com/review/{company_slug}"
    if current_page == 1:
        return f"{base_url}?stars={star}"
    return f"{base_url}?page={current_page}&stars={star}"


def build_trustpilot_natural_url(company_slug, current_page):
    base_url = f"https://fr.trustpilot.com/review/{company_slug}"
    if current_page == 1:
        return base_url
    return f"{base_url}?page={current_page}"


def parse_localized_number(value):
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return int(digits) if digits else None


def parse_decimal(value):
    match = re.search(r"\d+(?:[,.]\d+)?", str(value or ""))
    return float(match.group().replace(",", ".")) if match else None


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def parse_company_metadata(json_documents, distribution_texts, company_slug):
    metadata = {
        "name": None,
        "source_url": f"https://fr.trustpilot.com/review/{company_slug}",
        "trustpilot_slug": company_slug,
        "trustscore": None,
        "total_reviews": None,
        "rating_distribution": {str(star): None for star in range(1, 6)},
    }
    for raw_document in json_documents:
        try:
            document = json.loads(raw_document)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for candidate in _walk_json(document):
            aggregate = candidate.get("aggregateRating")
            if not isinstance(aggregate, dict):
                continue
            metadata["name"] = candidate.get("name") or metadata["name"]
            metadata["source_url"] = candidate.get("url") or metadata["source_url"]
            metadata["trustscore"] = parse_decimal(aggregate.get("ratingValue"))
            metadata["total_reviews"] = parse_localized_number(
                aggregate.get("reviewCount") or aggregate.get("ratingCount")
            )
            break
    for star, text in distribution_texts.items():
        match = re.search(r"(\d+(?:[,.]\d+)?)\s*%", str(text or ""))
        if match:
            metadata["rating_distribution"][str(star)] = float(
                match.group(1).replace(",", ".")
            )
    return metadata


def extract_company_metadata(page, company_slug):
    json_documents = page.locator(
        "script[type='application/ld+json']"
    ).all_text_contents()
    distribution_texts = {}
    for star in range(1, 6):
        selectors = [
            f"label[for='filter-review-score-{star}']",
            f"label[for*='star'][for$='-{star}']",
            f"input[name='stars'][value='{star}'] + label",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count():
                distribution_texts[star] = locator.first.inner_text()
                break
    return parse_company_metadata(json_documents, distribution_texts, company_slug)


def review_dedupe_key(review):
    source_review_id = str(review.get("source_review_id") or "").strip()
    if source_review_id:
        return f"id:{source_review_id}"
    return "|".join(
        re.sub(r"\s+", " ", str(review.get(field) or "").strip().lower())
        for field in ("author", "rating", "date", "verbatim")
    )


def extract_reviews_from_page(page, fallback_rating=None):
    reviews = []
    review_cards = page.query_selector_all("article[class*='styles_reviewCard']")
    for card in review_cards:
        try:
            author_elem = card.query_selector(
                "[data-user-profile-link-name='title'], "
                "span[class*='styles_consumerName']"
            )
            author = author_elem.inner_text().strip() if author_elem else "Anonyme"
            rating = str(fallback_rating or "")
            rating_container = card.query_selector(
                "div[class*='styles_reviewHeader'] div[data-star-rating], "
                "div[class*='styles_reviewHeader'] img"
            )
            if rating_container:
                rating = rating_container.get_attribute("data-star-rating") or rating
                alt_text = rating_container.get_attribute("alt") or ""
                alt_match = re.search(r"(?:Noté|Rated)\s+(\d)", alt_text)
                if alt_match:
                    rating = alt_match.group(1)
            date_elem = card.query_selector("[data-submission-date-typography='true'], time")
            date = date_elem.inner_text().strip() if date_elem else ""
            date = date.replace("Date de l'expérience :", "").strip()
            title_elem = card.query_selector(
                "[data-review-title-typography='true'], "
                "h2[data-service-review-title-typography='true']"
            )
            body_elem = card.query_selector(
                "[data-service-review-text-typography='true'], "
                "p[class*='typography_body-m']"
            )
            title_text = title_elem.inner_text().strip() if title_elem else ""
            body_text = body_elem.inner_text().strip() if body_elem else ""
            if title_text.endswith(("…", "...")):
                verbatim = body_text or title_text
            elif title_text and title_text.lower() in body_text.lower():
                verbatim = body_text
            else:
                verbatim = f"{title_text} - {body_text}".strip(" - ")
            reply_elem = card.query_selector(
                "[data-dashboard-reply-typography='true'], "
                "div[class*='styles_replyContainer']"
            )
            reply_text = reply_elem.inner_text().strip() if reply_elem else None
            review_link = card.query_selector("a[href*='/reviews/']")
            review_url = review_link.get_attribute("href") if review_link else None
            review_url = urljoin("https://fr.trustpilot.com", review_url) if review_url else None
            source_review_id = review_url.rstrip("/").split("/")[-1] if review_url else None
            if not verbatim and not rating:
                continue
            reviews.append(
                {
                    "source_review_id": source_review_id,
                    "review_url": review_url,
                    "author": author,
                    "rating": int(rating) if rating.isdigit() else None,
                    "date": date,
                    "verbatim": verbatim,
                    "company_responded": bool(reply_elem),
                    "company_reply_text": reply_text,
                }
            )
        except Exception:
            continue
    return reviews


def page_has_next(page):
    return any(
        page.locator(selector).count()
        for selector in (
            "a[rel='next']",
            "a[name='pagination-button-next']",
            "a[data-pagination-button-next-link='true']",
        )
    )


def collect_review_pages(
    fetch_page,
    company_slug,
    collection_mode=SAMPLED_MODE,
    stars_list=None,
    pages_per_star=2,
    max_pages=None,
):
    if collection_mode not in {SAMPLED_MODE, REPRESENTATIVE_MODE}:
        raise ValueError(f"Mode de collecte inconnu: {collection_mode}")
    stars_list = list(stars_list or [1, 2, 3, 4, 5])
    if collection_mode == SAMPLED_MODE:
        requests = [
            (build_trustpilot_review_url(company_slug, star, page_number), star, page_number)
            for star in stars_list
            for page_number in range(1, pages_per_star + 1)
        ]
        pages_requested = len(requests)
    else:
        requests = None
        pages_requested = max_pages
    reviews = []
    seen = set()
    metadata = None
    pages_processed = 0
    pages_succeeded = 0
    pages_failed = 0
    reviews_extracted = 0
    errors = []
    stop_reason = STOP_USER_LIMIT if collection_mode == SAMPLED_MODE else None

    def consume(url, star, page_number):
        nonlocal metadata, pages_processed, pages_succeeded, pages_failed
        nonlocal reviews_extracted, stop_reason
        pages_processed += 1
        try:
            result = fetch_page(url, star, page_number)
        except Exception as exc:
            pages_failed += 1
            errors.append({"page": page_number, "star": star, "error": str(exc)})
            stop_reason = STOP_ERROR
            return None
        if result.get("platform_limited"):
            pages_failed += 1
            stop_reason = STOP_PLATFORM_LIMITATION
            errors.append(
                {
                    "page": page_number,
                    "star": star,
                    "error": result.get("platform_reason")
                    or STOP_PLATFORM_LIMITATION,
                }
            )
            return result
        pages_succeeded += 1
        metadata = metadata or result.get("company")
        page_reviews = result.get("reviews", [])
        reviews_extracted += len(page_reviews)
        for review in page_reviews:
            key = review_dedupe_key(review)
            if key not in seen:
                seen.add(key)
                reviews.append(review)
        return result

    if collection_mode == SAMPLED_MODE:
        for url, star, page_number in requests:
            result = consume(url, star, page_number)
            if result is None or result.get("platform_limited"):
                break
    else:
        page_number = 1
        while True:
            if max_pages is not None and page_number > max_pages:
                stop_reason = STOP_USER_LIMIT
                break
            result = consume(
                build_trustpilot_natural_url(company_slug, page_number),
                None,
                page_number,
            )
            if result is None or result.get("platform_limited"):
                break
            if not result.get("reviews") or not result.get("has_next"):
                stop_reason = STOP_NATURAL_END
                break
            page_number += 1
    return {
        "company": metadata,
        "collection": {
            "mode": collection_mode,
            "pages_requested": pages_requested,
            "pages_processed": pages_processed,
            "pages_succeeded": pages_succeeded,
            "pages_failed": pages_failed,
            "reviews_extracted": reviews_extracted,
            "unique_reviews": len(reviews),
            "stop_reason": stop_reason or STOP_NATURAL_END,
            "errors": errors,
        },
        "reviews": reviews,
    }


def scrape_trustpilot(
    company_slug,
    output_path,
    collection_mode=SAMPLED_MODE,
    stars_list=None,
    pages_per_star=2,
    max_pages=None,
    company_domain=None,
    progress_callback=None,
):
    def notify(step, message, level="info"):
        if progress_callback:
            progress_callback(step=step, message=message, level=level)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 "
                "Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="fr-FR",
        )
        page = context.new_page()

        def fetch_page(url, star, page_number):
            notify("scrape_page", f"Lecture de {url}")
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            status = response.status if response else None
            if status in {403, 429}:
                return {
                    "platform_limited": True,
                    "platform_reason": f"http_{status}",
                    "reviews": [],
                }
            time.sleep(random.uniform(1.0, 2.0))
            cookie_button = page.query_selector("#onetrust-accept-btn-handler")
            if cookie_button and cookie_button.is_visible():
                cookie_button.click()
            body_text = page.locator("body").inner_text().lower()
            if "captcha" in body_text or "vérification" in body_text:
                return {
                    "platform_limited": True,
                    "platform_reason": "verification_page",
                    "reviews": [],
                }
            return {
                "company": extract_company_metadata(page, company_slug),
                "reviews": extract_reviews_from_page(page, fallback_rating=star),
                "has_next": page_has_next(page),
                "platform_limited": False,
            }

        result = collect_review_pages(
            fetch_page=fetch_page,
            company_slug=company_slug,
            collection_mode=collection_mode,
            stars_list=stars_list,
            pages_per_star=pages_per_star,
            max_pages=max_pages,
        )
        browser.close()
    company = result.get("company") or parse_company_metadata([], {}, company_slug)
    company["domain"] = company_domain
    result["company"] = company
    result["target_company"] = company_slug
    result["total_extracted"] = len(result["reviews"])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, ensure_ascii=False, indent=2)
    notify("scrape_output", f"Fichier JSON généré avec {len(result['reviews'])} avis.")
    return result


def scrape_trustpilot_by_stars(
    company_slug,
    output_path,
    stars_list=None,
    pages_per_star=2,
    progress_callback=None,
):
    return scrape_trustpilot(
        company_slug=company_slug,
        output_path=output_path,
        collection_mode=SAMPLED_MODE,
        stars_list=stars_list or [1, 2, 3],
        pages_per_star=pages_per_star,
        progress_callback=progress_callback,
    )


if __name__ == "__main__":
    scrape_trustpilot(
        company_slug="www.showroomprive.com",
        output_path="/app/data/showroom_reviews.json",
        collection_mode=SAMPLED_MODE,
        stars_list=[1, 2, 3, 4, 5],
        pages_per_star=2,
        company_domain="e-commerce",
    )
