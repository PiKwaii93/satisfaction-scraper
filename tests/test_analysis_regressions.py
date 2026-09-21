import unittest
from datetime import datetime

from app.api.services.analysis_service import parse_review_date
from app.api.services.insights import detect_topics


class ReviewDateParsingTests(unittest.TestCase):
    def test_parses_iso_date(self):
        self.assertEqual(parse_review_date("2026-06-01"), datetime(2026, 6, 1))

    def test_parses_french_date(self):
        self.assertEqual(parse_review_date("1 juin 2026"), datetime(2026, 6, 1))

    def test_empty_date_returns_none(self):
        self.assertIsNone(parse_review_date(""))

    def test_invalid_date_returns_none(self):
        self.assertIsNone(parse_review_date("date impossible"))

    def test_keeps_supported_relative_date_behavior(self):
        parsed = parse_review_date("il y a 2 jours")
        self.assertIsNotNone(parsed)
        self.assertLess(abs((datetime.now() - parsed).total_seconds() - 172800), 5)


class RefundTopicDetectionTests(unittest.TestCase):
    def test_detects_remboursement(self):
        self.assertIn("remboursement", detect_topics("remboursement"))

    def test_detects_rembourser(self):
        self.assertIn("remboursement", detect_topics("Je veux me faire rembourser"))

    def test_detects_remboursee(self):
        self.assertIn("remboursement", detect_topics("Commande remboursée"))

    def test_detects_plural_remboursements(self):
        self.assertIn("remboursement", detect_topics("Remboursements en attente"))

    def test_preserves_existing_delivery_topic(self):
        self.assertIn("livraison", detect_topics("Livraison en retard"))


if __name__ == "__main__":
    unittest.main()
