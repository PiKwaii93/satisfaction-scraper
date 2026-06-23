import pytest

from app.api.services.analysis_service import (
    build_csv_import_preview,
    normalize_company_slug,
    parse_reviews_csv,
)


def test_parse_reviews_csv_detects_common_columns():
    csv_content = (
        "avis,note,auteur,date,company_responded\n"
        "Commande recue rapidement,5,Alice,2026-06-01,oui\n"
        "Remboursement tres lent,1,Bob,2026-06-02,non\n"
        ",4,Ignored,2026-06-03,non\n"
    ).encode("utf-8")

    parsed = parse_reviews_csv(csv_content)

    assert len(parsed["reviews"]) == 2
    assert parsed["skipped_rows"] == 1
    assert parsed["detected_columns"]["verbatim"] == "avis"
    assert parsed["detected_columns"]["rating"] == "note"
    assert parsed["reviews"][0]["rating"] == 5
    assert parsed["reviews"][0]["company_responded"] is True


def test_parse_reviews_csv_uses_manual_mapping():
    csv_content = (
        "stars_count;customer_review;client_name\n"
        "5;Produit conforme;Alice\n"
        "2;Livraison trop lente;Bob\n"
    ).encode("utf-8")
    mapping = {
        "rating": "stars_count",
        "verbatim": "customer_review",
        "author": "client_name",
    }

    parsed = parse_reviews_csv(csv_content, column_mapping=mapping)

    assert len(parsed["reviews"]) == 2
    assert parsed["detected_columns"] == mapping
    assert parsed["reviews"][1]["author"] == "Bob"
    assert parsed["reviews"][1]["rating"] == 2


def test_build_csv_import_preview_returns_error_with_available_columns():
    csv_content = "stars_count;customer_review\n5;Produit conforme\n".encode("utf-8")

    preview = build_csv_import_preview(csv_content)

    assert preview["review_count"] == 0
    assert preview["available_columns"] == ["stars_count", "customer_review"]
    assert "Colonne obligatoire introuvable" in preview["error_message"]


def test_parse_reviews_csv_rejects_unknown_mapped_column():
    csv_content = "avis,note\nProduit conforme,5\n".encode("utf-8")

    with pytest.raises(ValueError, match="Colonne inconnue"):
        parse_reviews_csv(csv_content, column_mapping={"verbatim": "missing"})


def test_normalize_company_slug_accepts_trustpilot_urls_and_names():
    assert (
        normalize_company_slug("https://fr.trustpilot.com/review/www.darty.com")
        == "www.darty.com"
    )
    assert normalize_company_slug("Entreprise Test CSV") == "entreprise-test-csv"

