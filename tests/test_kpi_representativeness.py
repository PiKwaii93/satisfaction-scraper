from app.api.services.analysis_service import get_business_kpi_context, serialize_run


def test_sampled_run_is_not_representative_for_business_kpis():
    context = get_business_kpi_context(
        {
            "collection_mode": "sampled",
            "stop_reason": "user_limit",
            "reviews_extracted": 100,
            "unique_reviews": 95,
        }
    )

    assert context["is_representative_for_business_kpis"] is False
    assert "Échantillon analytique équilibré par étoiles" in context["business_kpi_warning"]


def test_successful_representative_run_is_representative_for_business_kpis():
    context = get_business_kpi_context(
        {
            "collection_mode": "representative",
            "stop_reason": "natural_end",
            "reviews_extracted": 120,
            "unique_reviews": 117,
        }
    )

    assert context == {
        "is_representative_for_business_kpis": True,
        "business_kpi_warning": None,
    }


def test_representative_run_stopped_at_user_limit_is_not_representative():
    context = get_business_kpi_context(
        {
            "collection_mode": "representative",
            "stop_reason": "user_limit",
            "reviews_extracted": 120,
            "unique_reviews": 117,
        }
    )

    assert context["is_representative_for_business_kpis"] is False
    assert "interrompue à une limite définie" in context["business_kpi_warning"]


def test_blocked_representative_run_without_reviews_is_not_representative():
    context = get_business_kpi_context(
        {
            "collection_mode": "representative",
            "stop_reason": "platform_limitation",
            "reviews_extracted": 0,
            "unique_reviews": 0,
        }
    )

    assert context["is_representative_for_business_kpis"] is False
    assert "Collecte représentative incomplète" in context["business_kpi_warning"]


def test_legacy_run_does_not_get_an_invented_collection_mode():
    context = get_business_kpi_context(
        {
            "collection_mode": None,
            "stop_reason": None,
            "reviews_extracted": 0,
            "unique_reviews": 0,
        }
    )

    assert context["is_representative_for_business_kpis"] is False
    assert "historique non déterminé" in context["business_kpi_warning"]


def test_legacy_run_serialization_preserves_unknown_collection_mode():
    run = serialize_run(
        {
            "run_id": 7,
            "company_id": 3,
            "organization_id": 2,
            "company_name": "Historique",
            "trustpilot_slug": "historique.test",
            "source": "trustpilot",
            "status": "completed",
            "collection_mode": None,
            "pages_per_star": 1,
            "stars_requested": "1,2,3,4,5",
            "reviews_extracted": 0,
            "unique_reviews": 0,
            "stop_reason": None,
            "total_reviews": 10,
        }
    )

    assert run["collection_mode"] is None
    assert run["is_representative_for_business_kpis"] is False
    assert "historique non déterminé" in run["business_kpi_warning"]
