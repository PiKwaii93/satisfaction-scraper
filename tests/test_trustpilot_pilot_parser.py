"""Anonymous fixtures for the Trustpilot pilot parser; no network or real reviews."""

import json
import importlib
import os
import unittest
from datetime import datetime
from unittest.mock import patch

from app.scraper import (
    collect_review_pages,
    extract_reviews_from_page,
    normalize_review_datetime,
    review_dedupe_key,
    REPRESENTATIVE_MODE,
)
from scripts.trustpilot_pilot_normalize import normalize_record, valid_project_record
from scripts.trustpilot_pilot_extract import date_details
from scripts import trustpilot_pilot_extract, trustpilot_pilot_normalize
from scripts.trustpilot_manual_check import connect_existing_browser


class Element:
    def __init__(self, text="", attributes=None, children=None):
        self.text = text
        self.attributes = attributes or {}
        self.children = children or {}

    def get_attribute(self, name):
        return self.attributes.get(name)

    def inner_text(self):
        return self.text

    def query_selector(self, selector):
        return self.children.get(selector)


class Card:
    def __init__(self, review_id=None, reply=True, legacy=False):
        self.review_id = review_id
        self.reply = reply
        self.legacy = legacy

    def query_selector(self, selector):
        if selector == "a[href*='/reviews/']":
            return Element(attributes={"href": f"/reviews/{self.review_id}"}) if self.review_id else None
        if "data-user-profile-link-name" in selector:
            return None
        if "styles_reviewHeader" in selector:
            return Element(attributes={"alt": "Noté 4 sur 5 étoiles"})
        if selector == "time[data-service-review-date-time-ago][datetime]":
            return None if self.legacy else Element(
                text="il y a 2 heures", attributes={"datetime": "2026-09-17T22:30:00Z"}
            )
        if selector == "[data-submission-date-typography='true']":
            return Element(text="17 septembre 2026") if self.legacy else None
        if selector == "time":
            return None
        if "data-review-title-typography" in selector:
            return Element(text="Titre anonyme")
        if "data-service-review-text-typography" in selector:
            return Element(text="Commentaire fictif.")
        if "data-service-review-business-reply-text-typography" in selector:
            if not self.reply:
                return None
            if self.legacy:
                return Element(
                    text="Réponse fictive.",
                    children={"time[datetime]": Element(attributes={"datetime": "2026-09-18T00:30:00Z"})},
                )
            return Element(text="Réponse fictive.")
        if selector == "time[data-service-review-business-reply-date-time-ago][datetime]":
            return (
                Element(attributes={"datetime": "2026-09-18T00:30:00Z"})
                if self.reply and not self.legacy else None
            )
        return None


class Page:
    def __init__(self, cards):
        self.cards = cards

    def query_selector_all(self, selector):
        assert selector == "article[class*='styles_reviewCard']"
        return self.cards


class TrustpilotDateTest(unittest.TestCase):
    def test_private_scripts_import_without_windows_environment(self):
        environment = {key: value for key, value in os.environ.items() if key != "LOCALAPPDATA"}
        with patch.dict(os.environ, environment, clear=True):
            importlib.reload(trustpilot_pilot_extract)
            importlib.reload(trustpilot_pilot_normalize)
            with self.assertRaisesRegex(RuntimeError, "LOCALAPPDATA"):
                trustpilot_pilot_extract.private_output_dir()
            with self.assertRaisesRegex(RuntimeError, "LOCALAPPDATA"):
                trustpilot_pilot_normalize.private_dir()

    def test_aware_iso_offsets_and_paris_midnight(self):
        self.assertEqual(normalize_review_datetime("2026-08-16T22:30:00Z"), "2026-08-17")
        self.assertEqual(normalize_review_datetime("2026-08-17T00:30:00+02:00"), "2026-08-17")
        self.assertEqual(normalize_review_datetime("2026-08-16T17:30:00-05:00"), "2026-08-17")
        self.assertEqual(normalize_review_datetime("2026-12-16T23:30:00+00:00"), "2026-12-17")
        self.assertEqual(normalize_review_datetime("2026-12-17T01:30:00+02:00"), "2026-12-17")

    def test_dst_boundary_and_invalid_input(self):
        self.assertEqual(normalize_review_datetime("2026-03-28T22:30:00Z"), "2026-03-28")
        self.assertEqual(normalize_review_datetime("2026-03-29T22:30:00Z"), "2026-03-30")
        self.assertEqual(normalize_review_datetime("2026-03-29T00:30:00Z"), "2026-03-29")
        self.assertEqual(normalize_review_datetime("2026-03-29T01:30:00Z"), "2026-03-29")
        self.assertEqual(normalize_review_datetime("2026-10-24T22:30:00Z"), "2026-10-25")
        self.assertEqual(normalize_review_datetime("2026-10-25T22:30:00Z"), "2026-10-25")
        self.assertEqual(normalize_review_datetime("2026-10-25T00:30:00Z"), "2026-10-25")
        self.assertEqual(normalize_review_datetime("2026-10-25T01:30:00Z"), "2026-10-25")
        self.assertIsNone(normalize_review_datetime("2026-09-17T22:30:00"))
        self.assertIsNone(normalize_review_datetime("not-a-date"))

    def test_review_and_reply_dates_from_iso(self):
        reviews = extract_reviews_from_page(Page([Card("review-a")]))
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["date"], "2026-09-18")
        self.assertEqual(reviews[0]["company_reply_date"], "2026-09-18")
        self.assertEqual(reviews[0]["company_reply_text"], "Réponse fictive.")
        self.assertEqual(datetime.strptime(reviews[0]["date"], "%Y-%m-%d").strftime("%Y-%m-%d"), reviews[0]["date"])

    def test_pilot_uses_iso_when_visible_date_is_relative(self):
        class RelativeDateCard:
            def query_selector(self, selector):
                return Element(
                    text="il y a 2 heures",
                    attributes={"datetime": "2026-09-17T22:30:00Z", "title": ""},
                )

        day, raw, matches, unverifiable = date_details(
            RelativeDateCard(), "time[data-service-review-date-time-ago]"
        )
        self.assertEqual(day, "2026-09-18")
        self.assertEqual(raw, "2026-09-17T22:30:00Z")
        self.assertTrue(matches)
        self.assertTrue(unverifiable)

    def test_cdp_attach_is_compatible_with_pinned_playwright(self):
        calls = []

        class Chromium:
            def connect_over_cdp(self, endpoint_url, *, timeout=None):
                calls.append((endpoint_url, timeout))
                return "existing-browser"

        class Playwright:
            chromium = Chromium()

        self.assertEqual(connect_existing_browser(Playwright()), "existing-browser")
        self.assertEqual(calls, [("http://127.0.0.1:9223", 10000)])

    def test_no_reply_and_legacy_date(self):
        reviews = extract_reviews_from_page(Page([Card("review-b", reply=False, legacy=True)]))
        self.assertEqual(reviews[0]["date"], "17 septembre 2026")
        self.assertFalse(reviews[0]["company_responded"])
        self.assertIsNone(reviews[0]["company_reply_date"])

    def test_legacy_reply_container(self):
        reviews = extract_reviews_from_page(Page([Card("review-c", legacy=True)]))
        self.assertTrue(reviews[0]["company_responded"])
        self.assertEqual(reviews[0]["company_reply_date"], "2026-09-18")

    def test_annex_card_and_duplicate_id_are_not_reviews(self):
        reviews = extract_reviews_from_page(Page([Card(None), Card("review-d"), Card("review-d")]))
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["source_review_id"], "review-d")

    def test_dedupe_across_pages_prefers_stable_id(self):
        def fetch_page(url, star, page_number):
            reviews = extract_reviews_from_page(
                Page([Card("review-e"), Card("review-f" if page_number == 1 else "review-g")])
            )
            return {"reviews": reviews, "has_next": page_number == 1}

        result = collect_review_pages(fetch_page, "example.test", collection_mode=REPRESENTATIVE_MODE)
        self.assertEqual(result["collection"]["reviews_extracted"], 4)
        self.assertEqual(result["collection"]["unique_reviews"], 3)
        self.assertEqual(len({review_dedupe_key(row) for row in result["reviews"]}), 3)

    def test_offline_normalization_preserves_fields_and_project_contract(self):
        original = {
            "source_review_id": "review-h",
            "review_url": "https://fr.trustpilot.com/reviews/review-h",
            "date": None,
            "review_datetime_utc": "2026-09-17T22:30:00Z",
            "rating": 4,
            "title": "Titre fictif",
            "verbatim": "Commentaire fictif.",
            "company_responded": True,
            "company_reply_text": "Réponse fictive.",
            "company_reply_date": None,
            "company_reply_datetime_utc": "2026-09-18T00:30:00Z",
        }
        normalized = normalize_record(original)
        self.assertIsNone(original["date"])
        self.assertEqual(normalized["date"], "2026-09-18")
        self.assertEqual(normalized["company_reply_date"], "2026-09-18")
        self.assertEqual(normalized["verbatim"], original["verbatim"])
        self.assertTrue(valid_project_record(normalized))
        self.assertEqual(json.loads(json.dumps(normalized)), normalized)


if __name__ == "__main__":
    unittest.main()
