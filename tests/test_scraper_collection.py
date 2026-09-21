import json
import unittest

from app.api.schemas import AnalysisRunCreate
from app.api.services.analysis_service import review_key
from app.scraper import (
    REPRESENTATIVE_MODE,
    SAMPLED_MODE,
    STOP_ERROR,
    STOP_NATURAL_END,
    STOP_PLATFORM_LIMITATION,
    STOP_USER_LIMIT,
    collect_review_pages,
    parse_company_metadata,
)


def review(review_id, rating=5):
    return {
        "source_review_id": review_id,
        "author": f"Auteur {review_id}",
        "rating": rating,
        "date": "20 septembre 2026",
        "verbatim": f"Avis {review_id}",
        "company_responded": False,
    }


class CompanyMetadataParsingTest(unittest.TestCase):
    def test_parses_real_values_and_distribution_without_defaults(self):
        json_ld = json.dumps(
            {
                "@type": "LocalBusiness",
                "name": "Entreprise Démonstration",
                "url": "https://example.test",
                "aggregateRating": {
                    "ratingValue": "4,3",
                    "reviewCount": "12 345",
                },
            }
        )

        metadata = parse_company_metadata(
            [json_ld],
            {1: "1 étoile 4 %", 5: "5 étoiles 72,5 %"},
            "example.test",
        )

        self.assertEqual(metadata["name"], "Entreprise Démonstration")
        self.assertEqual(metadata["trustscore"], 4.3)
        self.assertEqual(metadata["total_reviews"], 12345)
        self.assertEqual(metadata["rating_distribution"]["1"], 4.0)
        self.assertEqual(metadata["rating_distribution"]["5"], 72.5)
        self.assertIsNone(metadata["rating_distribution"]["3"])

    def test_missing_metadata_remains_explicitly_null(self):
        metadata = parse_company_metadata([], {}, "missing.test")

        self.assertIsNone(metadata["name"])
        self.assertIsNone(metadata["trustscore"])
        self.assertIsNone(metadata["total_reviews"])
        self.assertTrue(
            all(value is None for value in metadata["rating_distribution"].values())
        )


class CollectionPaginationTest(unittest.TestCase):
    def test_representative_mode_follows_natural_pages_and_deduplicates(self):
        calls = []

        def fetch_page(url, star, page_number):
            calls.append((url, star, page_number))
            pages = {
                1: [review("a"), review("b")],
                2: [review("b"), review("c")],
            }
            return {
                "company": {"name": "Entreprise"},
                "reviews": pages[page_number],
                "has_next": page_number == 1,
            }

        result = collect_review_pages(
            fetch_page,
            "example.test",
            collection_mode=REPRESENTATIVE_MODE,
        )

        self.assertEqual([call[1] for call in calls], [None, None])
        self.assertNotIn("stars=", calls[0][0])
        self.assertEqual(result["collection"]["pages_processed"], 2)
        self.assertEqual(result["collection"]["reviews_extracted"], 4)
        self.assertEqual(result["collection"]["unique_reviews"], 3)
        self.assertEqual(result["collection"]["stop_reason"], STOP_NATURAL_END)

    def test_representative_mode_stops_at_explicit_user_limit(self):
        def fetch_page(url, star, page_number):
            return {"reviews": [review(str(page_number))], "has_next": True}

        result = collect_review_pages(
            fetch_page,
            "example.test",
            collection_mode=REPRESENTATIVE_MODE,
            max_pages=3,
        )

        self.assertEqual(result["collection"]["pages_requested"], 3)
        self.assertEqual(result["collection"]["pages_processed"], 3)
        self.assertEqual(result["collection"]["stop_reason"], STOP_USER_LIMIT)

    def test_sampled_mode_keeps_equal_page_budget_per_star(self):
        calls = []

        def fetch_page(url, star, page_number):
            calls.append((url, star, page_number))
            return {"reviews": [review(f"{star}-{page_number}", star)], "has_next": True}

        result = collect_review_pages(
            fetch_page,
            "example.test",
            collection_mode=SAMPLED_MODE,
            stars_list=[1, 5],
            pages_per_star=2,
        )

        self.assertEqual(result["collection"]["pages_requested"], 4)
        self.assertEqual(result["collection"]["pages_processed"], 4)
        self.assertEqual([call[1] for call in calls], [1, 1, 5, 5])
        self.assertTrue(all("stars=" in call[0] for call in calls))
        self.assertEqual(result["collection"]["stop_reason"], STOP_USER_LIMIT)

    def test_page_error_is_counted_and_reported(self):
        def fetch_page(url, star, page_number):
            raise RuntimeError("page indisponible")

        result = collect_review_pages(
            fetch_page,
            "example.test",
            collection_mode=REPRESENTATIVE_MODE,
            max_pages=10,
        )

        self.assertEqual(result["collection"]["pages_processed"], 1)
        self.assertEqual(result["collection"]["pages_failed"], 1)
        self.assertEqual(result["collection"]["stop_reason"], STOP_ERROR)
        self.assertIn("page indisponible", result["collection"]["errors"][0]["error"])

    def test_platform_limitation_is_explicit(self):
        def fetch_page(url, star, page_number):
            return {
                "reviews": [],
                "platform_limited": True,
                "platform_reason": "http_403",
            }

        result = collect_review_pages(
            fetch_page,
            "example.test",
            collection_mode=REPRESENTATIVE_MODE,
        )

        self.assertEqual(result["collection"]["pages_processed"], 1)
        self.assertEqual(result["collection"]["pages_failed"], 1)
        self.assertEqual(
            result["collection"]["stop_reason"], STOP_PLATFORM_LIMITATION
        )
        self.assertEqual(result["collection"]["errors"][0]["error"], "http_403")


class CollectionContractTest(unittest.TestCase):
    def test_request_distinguishes_sampled_and_representative_modes(self):
        sampled = AnalysisRunCreate(company="example.test")
        representative = AnalysisRunCreate(
            company="example.test",
            domain="e-commerce",
            collection_mode="representative",
            max_pages=25,
        )

        self.assertEqual(sampled.collection_mode, SAMPLED_MODE)
        self.assertIsNone(sampled.max_pages)
        self.assertEqual(representative.collection_mode, REPRESENTATIVE_MODE)
        self.assertEqual(representative.max_pages, 25)
        self.assertEqual(representative.domain, "e-commerce")

    def test_persistence_key_prefers_source_review_id(self):
        first = review("trustpilot-id", rating=1)
        second = review("trustpilot-id", rating=5)
        second["author"] = "Autre auteur"
        second["verbatim"] = "Texte modifié"

        self.assertEqual(review_key(first), review_key(second))


if __name__ == "__main__":
    unittest.main()
