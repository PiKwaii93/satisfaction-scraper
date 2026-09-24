"""Two-page, private Trustpilot pilot using an already-open local CDP browser.

Run only after explicit approval. This script never launches or closes Chrome,
reads no browser credentials, and does not write into the repository.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.scraper import normalize_review_datetime
from scripts.trustpilot_manual_check import COMPANY, PAGES, connect_existing_browser, is_challenge


BASE_URL = "https://fr.trustpilot.com"
CARD_SELECTOR = "article[class*='styles_reviewCard']"
LINK_SELECTOR = "a[href*='/reviews/']"
TITLE_SELECTOR = "[data-review-title-typography='true'], h2[data-service-review-title-typography='true']"
TEXT_SELECTOR = "[data-service-review-text-typography='true'], p[class*='typography_body-m']"
RATING_SELECTOR = "div[class*='styles_reviewHeader'] img[alt], div[class*='styles_reviewHeader'] [data-star-rating]"
REVIEW_DATE_SELECTOR = "time[data-service-review-date-time-ago]"
REPLY_TITLE_SELECTOR = "[data-service-review-business-reply-title-typography]"
REPLY_TEXT_SELECTOR = "[data-service-review-business-reply-text-typography]"
REPLY_DATE_SELECTOR = "time[data-service-review-business-reply-date-time-ago]"
OUTPUT_DIR = Path(os.environ["LOCALAPPDATA"]) / "SatisfactionClient" / "TrustpilotPilot"
FRENCH_MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}


def read_text(card, selector: str) -> str:
    element = card.query_selector(selector)
    return element.inner_text().strip() if element else ""


def french_calendar_date(value: str) -> str | None:
    normalized = unicodedata.normalize("NFKD", value.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    match = re.search(r"\b(\d{1,2})\s+([a-z]+)\s+(\d{4})\b", normalized)
    if not match or match.group(2) not in FRENCH_MONTHS:
        return None
    try:
        return date(int(match.group(3)), FRENCH_MONTHS[match.group(2)], int(match.group(1))).isoformat()
    except ValueError:
        return None


def date_details(card, selector: str) -> tuple[str | None, str | None, bool, bool]:
    element = card.query_selector(selector)
    if not element:
        return None, None, False, True
    raw_date = element.get_attribute("datetime") or ""
    visible_date = element.inner_text().strip()
    tooltip_date = element.get_attribute("title") or ""
    day = normalize_review_datetime(raw_date)
    display_day = french_calendar_date(visible_date)
    tooltip_day = french_calendar_date(tooltip_date)
    observed_days = [value for value in (display_day, tooltip_day) if value]
    return day, raw_date or None, bool(day and all(value == day for value in observed_days)), not observed_days


def parse_card(card) -> tuple[dict | None, dict]:
    link = card.query_selector(LINK_SELECTOR)
    if not link:
        return None, {"reason": "no_review_link"}
    href = link.get_attribute("href") or ""
    review_url = urljoin(BASE_URL, href)
    parsed_url = urlparse(review_url)
    match = re.fullmatch(r"/reviews/([A-Za-z0-9_-]+)", parsed_url.path.rstrip("/"))
    if parsed_url.hostname != "fr.trustpilot.com" or not match:
        return None, {"reason": "invalid_review_link"}

    rating_element = card.query_selector(RATING_SELECTOR)
    raw_rating = (
        (rating_element.get_attribute("data-star-rating") or rating_element.get_attribute("alt") or "")
        if rating_element else ""
    )
    rating_match = re.search(r"(?:Noté|Rated)\s+([1-5])\b", raw_rating, re.IGNORECASE)
    rating = int(raw_rating) if raw_rating in {"1", "2", "3", "4", "5"} else (
        int(rating_match.group(1)) if rating_match else None
    )
    review_date, review_datetime_utc, date_matches_display, date_display_unverifiable = date_details(
        card, REVIEW_DATE_SELECTOR
    )
    reply_present = bool(card.query_selector(REPLY_TITLE_SELECTOR))
    reply_date, reply_datetime_utc, reply_date_matches_display, reply_date_display_unverifiable = date_details(
        card, REPLY_DATE_SELECTOR
    )
    title = read_text(card, TITLE_SELECTOR)
    verbatim = read_text(card, TEXT_SELECTOR)
    reply_text = read_text(card, REPLY_TEXT_SELECTOR) if reply_present else None

    record = {
        "source_review_id": match.group(1),
        "review_url": review_url,
        "date": review_date,
        "review_datetime_utc": review_datetime_utc,
        "rating": rating,
        "title": title,
        "verbatim": verbatim,
        "company_responded": reply_present,
        "company_reply_text": reply_text,
        "company_reply_date": reply_date if reply_present else None,
        "company_reply_datetime_utc": reply_datetime_utc if reply_present else None,
    }
    checks = {
        "rating_invalid": rating is None,
        "date_missing_or_invalid": review_date is None,
        "date_display_mismatch": bool(review_date and not date_matches_display),
        "date_display_unverifiable": date_display_unverifiable,
        "title_missing": not title,
        "text_missing": not verbatim,
        "reply_text_missing": bool(reply_present and not reply_text),
        "reply_date_missing_or_invalid": bool(reply_present and not reply_date),
        "reply_date_display_mismatch": bool(reply_present and reply_date and not reply_date_matches_display),
        "reply_date_display_unverifiable": bool(reply_present and reply_date_display_unverifiable),
    }
    return record, checks


def expected_url(page_number: int) -> str:
    return f"{BASE_URL}/review/{COMPANY}?page={page_number}"


def is_expected_final_url(url: str, page_number: int) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "fr.trustpilot.com"
        and parsed.path == f"/review/{COMPANY}"
        and parse_qs(parsed.query).get("page") == [str(page_number)]
    )


def project_fields_compatible(record: dict) -> bool:
    return (
        isinstance(record.get("source_review_id"), str)
        and bool(record["source_review_id"])
        and isinstance(record.get("review_url"), str)
        and isinstance(record.get("date"), str)
        and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"]))
        and isinstance(record.get("rating"), int)
        and 1 <= record["rating"] <= 5
        and isinstance(record.get("verbatim"), str)
        and bool(record["verbatim"])
        and isinstance(record.get("company_responded"), bool)
        and (record.get("company_reply_text") is None or isinstance(record["company_reply_text"], str))
    )


def save_json(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    with path.open("r", encoding="utf-8") as source:
        loaded = json.load(source)
    if loaded != payload:
        raise RuntimeError("Le JSON pilote écrit ne correspond pas aux données extraites.")


def save_report(path: Path, started_at: str, summaries: list[dict], stop_reason: str | None) -> None:
    lines = [
        "# Validation du pilote Trustpilot",
        "",
        f"- Début UTC : {started_at}",
        f"- Fin UTC : {datetime.now(timezone.utc).isoformat()}",
        "- Entreprise : Showroomprivé (`www.showroomprive.com`)",
        "- Navigateur : Chrome existant, connexion CDP locale, session ouverte manuellement",
        "- Pages autorisées : 11 et 50 uniquement ; aucun autre avis consulté par le script",
        "- Identifiants, profils, cookies et en-têtes d'authentification : non extraits",
        f"- Arrêt anticipé : {stop_reason or 'aucun'}",
        "",
        "| Page | URL | HTTP | Redirection | Cartes totales | Cartes visibles | Avis à ID unique | Avis complets | Réponses | Fichier |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['page']} | {row['source_url']} | {row.get('http_status', '—')} | "
            f"{row.get('redirected', '—')} | {row.get('cards_total', '—')} | "
            f"{row.get('cards_visible', '—')} | {row.get('reviews_saved', '—')} | "
            f"{row.get('fully_valid_reviews', '—')} | "
            f"{row.get('replies_detected', '—')} | {row.get('file', '—')} |"
        )
    lines += ["", "## Contrôles", ""]
    lines.append(f"- Avis à identifiant unique enregistrés : {sum(row.get('reviews_saved', 0) for row in summaries)}")
    lines.append(f"- Avis complets : {sum(row.get('fully_valid_reviews', 0) for row in summaries)}")
    lines.append(f"- Doublons interpages : {sum(row.get('duplicates_across_pages', 0) for row in summaries)}")
    lines.append("")
    for row in summaries:
        if "checks" not in row:
            continue
        lines.append(f"### Page {row['page']}")
        lines.append("")
        lines.append(f"- Cartes sans lien d'avis : {row['cards_without_id']}")
        lines.append(f"- Identifiants dupliqués sur la page : {row['duplicates_on_page']}")
        lines.append(f"- Identifiants déjà vus sur l'autre page : {row['duplicates_across_pages']}")
        lines.append(f"- Avis compatibles avec les champs consommés par le projet : {row['project_compatible_reviews']}")
        for name, count in row["checks"].items():
            lines.append(f"- {name} : {count}")
        lines.append("")
    lines += [
        "`date` et `company_reply_date` sont les jours civils Europe/Paris dérivés "
        "des attributs `<time datetime>`, normalisés en `YYYY-MM-DD`. Les horodatages "
        "sont conservés séparément ; les dates relatives visibles ne permettent pas "
        "toujours une vérification indépendante du jour.",
        "`verbatim` est le texte du commentaire. `title` et `company_reply_date` "
        "sont des champs supplémentaires ; les autres champs d'avis suivent les noms consommés "
        "par le JSON du projet. Aucun import applicatif ou SQL n'a été lancé.",
        "Aucun fichier JSON Schema formel n'est versionné pour ce payload : le contrôle "
        "de compatibilité porte sur les champs et types effectivement consommés par le code.",
        "Le total affiché par Trustpilot n'est pas compté comme avis collecté.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    if OUTPUT_DIR.resolve().is_relative_to(repo):
        raise RuntimeError("Le dossier pilote doit rester hors Git.")
    started_at = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summaries: list[dict] = []
    seen_ids: set[str] = set()
    stop_reason = None
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        try:
            browser = connect_existing_browser(playwright)
        except PlaywrightError:
            stop_reason = "Connexion CDP impossible ; aucune navigation"
        else:
            if len(browser.contexts) != 1:
                stop_reason = "Contexte CDP absent ou ambigu ; aucune navigation"
            else:
                context = browser.contexts[0]
                existing_page = next(
                    (page for page in context.pages if is_expected_final_url(page.url, 50)),
                    None,
                )
                page = existing_page or context.new_page()
                blocked_responses: list[int] = []

                def on_response(response) -> None:
                    host = urlparse(response.url).hostname or ""
                    if (host == "trustpilot.com" or host.endswith(".trustpilot.com")) and response.status in (403, 429):
                        blocked_responses.append(response.status)

                page.on("response", on_response)
                for number in PAGES:
                    source_url = expected_url(number)
                    summary: dict = {"page": number, "source_url": source_url}
                    summaries.append(summary)
                    try:
                        response = page.goto(source_url, wait_until="commit", timeout=30000)
                        status = response.status if response else None
                        summary["http_status"] = status
                        if status in (403, 429) or blocked_responses:
                            stop_reason = f"HTTP {status or blocked_responses[0]} sur la page {number}"
                            break
                        if status != 200:
                            stop_reason = f"HTTP inattendu {status} sur la page {number}"
                            break
                        page.wait_for_load_state("domcontentloaded", timeout=15000)
                        if blocked_responses or is_challenge(page):
                            stop_reason = f"Blocage ou vérification sur la page {number}"
                            break
                        summary["redirected"] = bool(response.request.redirected_from) if response else False
                        if not is_expected_final_url(page.url, number):
                            stop_reason = f"Redirection inattendue sur la page {number} ; URL finale masquée"
                            break
                        cards = page.query_selector_all(CARD_SELECTOR)
                        summary["cards_total"] = len(cards)
                        summary["cards_visible"] = sum(card.is_visible() for card in cards)
                        if not cards:
                            stop_reason = f"Aucune carte détectée sur la page {number}"
                            break
                        records = []
                        fully_valid_reviews = 0
                        page_ids: set[str] = set()
                        checks = {}
                        summary["cards_without_id"] = 0
                        summary["duplicates_on_page"] = 0
                        summary["duplicates_across_pages"] = 0
                        for card in cards:
                            if not card.is_visible():
                                continue
                            record, card_checks = parse_card(card)
                            if record is None:
                                summary["cards_without_id"] += 1
                                continue
                            review_id = record["source_review_id"]
                            if review_id in page_ids:
                                summary["duplicates_on_page"] += 1
                                continue
                            page_ids.add(review_id)
                            if review_id in seen_ids:
                                summary["duplicates_across_pages"] += 1
                                continue
                            seen_ids.add(review_id)
                            records.append(record)
                            if not any(
                                issue for name, issue in card_checks.items()
                                if not name.endswith("_unverifiable")
                            ):
                                fully_valid_reviews += 1
                            for name, issue in card_checks.items():
                                checks[name] = checks.get(name, 0) + int(issue)
                        summary["checks"] = checks
                        summary["reviews_saved"] = len(records)
                        summary["fully_valid_reviews"] = fully_valid_reviews
                        summary["project_compatible_reviews"] = sum(
                            project_fields_compatible(record) for record in records
                        )
                        summary["replies_detected"] = sum(record["company_responded"] for record in records)
                        if blocked_responses or is_challenge(page):
                            stop_reason = f"Blocage ou vérification après lecture de la page {number}"
                            break
                        filename = f"showroomprive_page_{number}_{stamp}.json"
                        save_json(
                            OUTPUT_DIR / filename,
                            {
                                "source": "trustpilot",
                                "target_company": COMPANY,
                                "source_url": source_url,
                                "page": number,
                                "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                                "cards_detected": len(cards),
                                "reviews_extracted": len(records),
                                "reviews": records,
                            },
                        )
                        summary["file"] = filename
                    except PlaywrightTimeoutError:
                        stop_reason = f"Timeout sur la page {number} ; aucune nouvelle tentative"
                        break
                    except PlaywrightError:
                        stop_reason = f"Erreur de navigation ou de lecture sur la page {number} ; aucune nouvelle tentative"
                        break

    report_path = OUTPUT_DIR / f"validation_{stamp}.md"
    save_report(report_path, started_at, summaries, stop_reason)
    print(f"Rapport : %LOCALAPPDATA%\\SatisfactionClient\\TrustpilotPilot\\{report_path.name}")
    for summary in summaries:
        print(
            f"Page {summary['page']} : HTTP {summary.get('http_status')} ; "
            f"cartes {summary.get('cards_total')} ; avis enregistrés {summary.get('reviews_saved')}."
        )
    print(f"Arrêt anticipé : {stop_reason or 'aucun'}")
    print("Chrome existant laissé ouvert ; aucun profil, cookie ou avis affiché dans ce terminal.")


if __name__ == "__main__":
    main()
