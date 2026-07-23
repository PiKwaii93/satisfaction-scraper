from datetime import date

from app.api.services.customer_action_service import _build_customer_action_playbook


def test_builds_topic_playbook_from_alert_metadata():
    playbook = _build_customer_action_playbook(
        {
            "alert_type": "rising_irritant",
            "severity": "critical",
            "message": "Livraison augmente de 35 occurrence(s).",
            "metadata": {"topic": "livraison"},
        }
    )

    assert playbook["title"] == "Reduire l'irritant Livraison"
    assert playbook["priority"] == "critical"
    assert playbook["owner_name"] == "Responsable experience client"
    assert isinstance(playbook["due_date"], date)
    assert "Auditer les transporteurs" in playbook["notes"]
    assert "Mesure de succes" in playbook["notes"]


def test_builds_negative_share_playbook_from_json_metadata():
    playbook = _build_customer_action_playbook(
        {
            "alert_type": "negative_share_high",
            "severity": "warning",
            "message": "53.6% des avis sont negatifs.",
            "metadata": '{"negative_rate": 53.6}',
        }
    )

    assert playbook["title"] == "Reduire la part d'avis negatifs"
    assert playbook["priority"] == "high"
    assert playbook["owner_name"] == "Responsable service client"
    assert "avis negatifs" in playbook["notes"]
    assert "Diminution de la part d'avis negatifs" in playbook["notes"]
