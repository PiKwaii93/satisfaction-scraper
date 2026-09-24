"""Two-page Trustpilot check over local CDP; no review extraction."""

from __future__ import annotations

import argparse
import inspect
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


COMPANY = "www.showroomprive.com"
PAGES = (11, 50)
CDP_ENDPOINT = "http://127.0.0.1:9223"
CARD_SELECTOR = "article[class*='styles_reviewCard']:visible"
CHALLENGE_SELECTOR = (
    "iframe[src*='recaptcha']:visible, iframe[src*='hcaptcha']:visible, "
    "iframe[src*='challenges.cloudflare.com']:visible, "
    "[id='captcha']:visible, [id='challenge-running']:visible, "
    "form[action*='challenge' i]:visible"
)
CHALLENGE_MARKERS = (
    "captcha",
    "just a moment",
    "attention required",
    "verify you are human",
    "vérifiez que vous êtes un humain",
)


def is_challenge(page) -> bool:
    location = page.url.lower()
    if "captcha" in location or "challenge" in location:
        return True
    title = page.title().lower()
    return any(marker in title for marker in CHALLENGE_MARKERS) or page.locator(CHALLENGE_SELECTOR).count() > 0


def connect_existing_browser(playwright):
    """Attach to the dedicated Chrome, preserving defaults when supported.

    no_defaults was introduced after the project's pinned Playwright 1.44.
    """
    connect = playwright.chromium.connect_over_cdp
    options = {"timeout": 10000}
    if "no_defaults" in inspect.signature(connect).parameters:
        options["no_defaults"] = True
    return connect(CDP_ENDPOINT, **options)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostic limité des pages Trustpilot 11 et 50")
    parser.add_argument("--page", type=int, choices=PAGES, help="Une seule page, sans retester l'autre")
    args = parser.parse_args()
    pages_to_check = (args.page,) if args.page else PAGES
    with sync_playwright() as playwright:
        try:
            browser = connect_existing_browser(playwright)
        except PlaywrightError:
            print("Connexion CDP impossible. Aucun navigateur ou profil n'a été lancé par ce script.")
            return
        print("Connexion CDP réussie.")
        if len(browser.contexts) != 1:
            print(f"Contexte existant ambigu ({len(browser.contexts)} contextes). Arrêt sans navigation.")
            return
        context = browser.contexts[0]
        print("Contexte existant récupéré.")
        existing_diagnostic = next(
            (
                candidate
                for candidate in context.pages
                if urlparse(candidate.url).hostname == "fr.trustpilot.com"
                and urlparse(candidate.url).path == f"/review/{COMPANY}"
                and parse_qs(urlparse(candidate.url).query).get("page") == ["11"]
            ),
            None,
        )
        page = existing_diagnostic if args.page == 50 and existing_diagnostic else context.new_page()
        blocked_responses: list[int] = []

        def on_response(response) -> None:
            host = urlparse(response.url).hostname or ""
            if (host == "trustpilot.com" or host.endswith(".trustpilot.com")) and response.status in (403, 429):
                blocked_responses.append(response.status)

        page.on("response", on_response)
        for number in pages_to_check:
            if blocked_responses:
                print(f"Arrêt : HTTP {blocked_responses[0]} reçu ; aucune autre page visitée.")
                return
            url = f"https://fr.trustpilot.com/review/{COMPANY}?page={number}"
            try:
                response = page.goto(url, wait_until="commit", timeout=30000)
                status = response.status if response else None
                print(f"Page {number} : HTTP {status}.")
                if status in (403, 429) or blocked_responses:
                    print(f"Page {number} : HTTP {status or blocked_responses[0]}. Arrêt immédiat.")
                    return
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                if blocked_responses:
                    print(f"Page {number} : HTTP {blocked_responses[0]} reçu. Arrêt immédiat.")
                    return
                if is_challenge(page):
                    print(f"Page {number} : CAPTCHA ou page de vérification détecté. Arrêt immédiat.")
                    return
                final_url = urlparse(page.url)
                redirected = response.request.redirected_from is not None if response else False
                if (
                    final_url.hostname != "fr.trustpilot.com"
                    or final_url.path != f"/review/{COMPANY}"
                    or parse_qs(final_url.query).get("page") != [str(number)]
                ):
                    print(f"Page {number} : HTTP {status} ; redirection inattendue vers {final_url.hostname or 'URL masquée'} ; arrêt.")
                    return
                if status != 200:
                    print(f"Page {number} : HTTP {status}. Arrêt sans autre navigation.")
                    return
                cards = page.locator(CARD_SELECTOR)
                cards.first.wait_for(state="visible", timeout=5000)
                if blocked_responses or is_challenge(page):
                    print(f"Page {number} : blocage ou vérification apparu après chargement. Arrêt immédiat.")
                    return
                print(f"Page {number} : HTTP 200 ; URL finale {page.url} ; redirection={redirected} ; cartes visibles={cards.count()}.")
            except PlaywrightTimeoutError:
                print(f"Page {number} : délai dépassé. Arrêt sans nouvelle tentative.")
                return
            except PlaywrightError:
                print(f"Page {number} : erreur de navigation. Arrêt sans nouvelle tentative.")
                return
        print("Test limité terminé ; aucun avis extrait.")


if __name__ == "__main__":
    main()
