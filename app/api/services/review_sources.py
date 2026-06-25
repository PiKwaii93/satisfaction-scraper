from psycopg2.extras import Json

from app.api.database import get_cursor


ACTIVE_SOURCE_STATUS = "active"
NOT_CONFIGURED_SOURCE_STATUS = "not_configured"
ERROR_SOURCE_STATUS = "error"
PLANNED_SOURCE_STATUS = "planned"


CSV_COLUMN_ALIASES = {
    "verbatim": [
        "avis",
        "review",
        "text",
        "texte",
        "comment",
        "commentaire",
        "body",
        "message",
    ],
    "rating": ["note", "stars", "etoiles", "score"],
    "author": ["author_name", "auteur", "nom", "name", "user", "client"],
    "date": ["raw_date", "review_date", "created_at", "published_at"],
    "company_responded": ["responded", "response", "reponse", "has_response"],
}


SOURCE_CATALOG = [
    {
        "source_id": "trustpilot",
        "label": "Trustpilot",
        "status": ACTIVE_SOURCE_STATUS,
        "category": "web public",
        "description": "Collecte des avis publics Trustpilot par entreprise et par note.",
        "primary_action": "Coller une URL ou un domaine Trustpilot",
        "setup_hint": "Aucune configuration requise pour le MVP.",
        "supports_analysis": True,
        "is_configured": True,
        "required_fields": ["URL ou domaine Trustpilot"],
        "optional_fields": ["Pages par note", "Notes ciblees"],
        "column_aliases": {},
    },
    {
        "source_id": "csv",
        "label": "CSV",
        "status": ACTIVE_SOURCE_STATUS,
        "category": "import fichier",
        "description": "Import d'un fichier d'avis client fourni par une entreprise.",
        "primary_action": "Importer un fichier CSV",
        "setup_hint": "Format flexible avec mapping manuel des colonnes.",
        "supports_analysis": True,
        "is_configured": True,
        "required_fields": ["verbatim"],
        "optional_fields": ["rating", "author", "date", "company_responded"],
        "column_aliases": CSV_COLUMN_ALIASES,
    },
    {
        "source_id": "google_reviews",
        "label": "Google Reviews",
        "status": PLANNED_SOURCE_STATUS,
        "category": "connecteur API",
        "description": "Preparation d'un connecteur Google Business Profile pour les avis etablissements.",
        "primary_action": None,
        "setup_hint": "Necessitera OAuth, droits Business Profile et respect des quotas API.",
        "supports_analysis": False,
        "is_configured": False,
        "required_fields": ["Compte Google Business Profile"],
        "optional_fields": ["Etablissements", "Periode"],
        "column_aliases": {},
    },
    {
        "source_id": "zendesk",
        "label": "Zendesk",
        "status": PLANNED_SOURCE_STATUS,
        "category": "support client",
        "description": "Preparation d'une source SAV pour analyser tickets, motifs et verbatims clients.",
        "primary_action": None,
        "setup_hint": "Necessitera une cle API Zendesk et un mapping des champs tickets.",
        "supports_analysis": False,
        "is_configured": False,
        "required_fields": ["Sous-domaine Zendesk", "Token API"],
        "optional_fields": ["Tags", "Periode", "Statuts"],
        "column_aliases": {},
    },
    {
        "source_id": "shopify",
        "label": "Shopify",
        "status": PLANNED_SOURCE_STATUS,
        "category": "e-commerce",
        "description": "Preparation d'une source e-commerce pour rapprocher avis, commandes et produits.",
        "primary_action": None,
        "setup_hint": "Necessitera une app Shopify et une strategie de donnees produits.",
        "supports_analysis": False,
        "is_configured": False,
        "required_fields": ["Boutique Shopify", "App token"],
        "optional_fields": ["Produits", "Commandes", "Periode"],
        "column_aliases": {},
    },
    {
        "source_id": "internal_support",
        "label": "SAV interne",
        "status": PLANNED_SOURCE_STATUS,
        "category": "donnees internes",
        "description": "Preparation d'une source generique pour exports CRM, SAV ou enquete post-achat.",
        "primary_action": None,
        "setup_hint": "Le CSV couvre deja une partie de ce besoin dans le MVP.",
        "supports_analysis": False,
        "is_configured": False,
        "required_fields": ["Export client"],
        "optional_fields": ["Canal", "Motif", "Date", "Agent"],
        "column_aliases": {},
    },
]


SOURCE_CATALOG_BY_ID = {source["source_id"]: source for source in SOURCE_CATALOG}


def _default_source_state(source):
    if source["status"] == PLANNED_SOURCE_STATUS:
        return {
            "is_enabled": False,
            "is_configured": False,
            "status": PLANNED_SOURCE_STATUS,
            "config": {},
            "last_error": None,
        }

    return {
        "is_enabled": True,
        "is_configured": True,
        "status": ACTIVE_SOURCE_STATUS,
        "config": {},
        "last_error": None,
    }


def _serialize_source(source, row=None):
    state = _default_source_state(source)
    if row:
        state.update(
            {
                "is_enabled": bool(row.get("is_enabled")),
                "is_configured": bool(row.get("is_configured")),
                "status": row.get("status") or state["status"],
                "config": row.get("config") or {},
                "last_error": row.get("last_error"),
            }
        )

    if source["status"] == PLANNED_SOURCE_STATUS:
        status = PLANNED_SOURCE_STATUS
    elif state["last_error"] or state["status"] == ERROR_SOURCE_STATUS:
        status = ERROR_SOURCE_STATUS
    elif not state["is_enabled"] or not state["is_configured"]:
        status = NOT_CONFIGURED_SOURCE_STATUS
    else:
        status = ACTIVE_SOURCE_STATUS

    supports_analysis = source["supports_analysis"] and status == ACTIVE_SOURCE_STATUS
    return {
        **source,
        "status": status,
        "supports_analysis": supports_analysis,
        "is_configured": status == ACTIVE_SOURCE_STATUS,
        "is_enabled": state["is_enabled"],
        "can_configure": source["status"] != PLANNED_SOURCE_STATUS,
        "last_error": state["last_error"],
        "config": state["config"],
        "updated_at": row.get("updated_at") if row else None,
    }


def _default_sources():
    return [_serialize_source(source) for source in SOURCE_CATALOG]


def ensure_organization_source_rows(organization_id):
    with get_cursor(commit=True) as cursor:
        for source in SOURCE_CATALOG:
            state = _default_source_state(source)
            cursor.execute(
                """
                INSERT INTO organization_review_sources (
                    organization_id,
                    source_id,
                    is_enabled,
                    is_configured,
                    status,
                    config,
                    last_error
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, source_id) DO NOTHING;
                """,
                (
                    organization_id,
                    source["source_id"],
                    state["is_enabled"],
                    state["is_configured"],
                    state["status"],
                    Json(state["config"]),
                    state["last_error"],
                ),
            )


def list_review_sources(organization_id=None):
    if organization_id is None:
        return _default_sources()

    try:
        ensure_organization_source_rows(organization_id)
        with get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    source_id,
                    is_enabled,
                    is_configured,
                    status,
                    config,
                    last_error,
                    updated_at
                FROM organization_review_sources
                WHERE organization_id = %s;
                """,
                (organization_id,),
            )
            rows = {row["source_id"]: row for row in cursor.fetchall()}
    except Exception:
        return _default_sources()

    return [
        _serialize_source(source, rows.get(source["source_id"]))
        for source in SOURCE_CATALOG
    ]


def update_review_source(organization_id, source_id, payload):
    source = SOURCE_CATALOG_BY_ID.get(source_id)
    if source is None:
        raise ValueError("Source d'avis inconnue.")

    if source["status"] == PLANNED_SOURCE_STATUS:
        raise ValueError("Ce connecteur est planifie mais pas encore configurable.")

    ensure_organization_source_rows(organization_id)
    enabled = payload.enabled

    with get_cursor(commit=True) as cursor:
        if enabled is None:
            cursor.execute(
                """
                SELECT *
                FROM organization_review_sources
                WHERE organization_id = %s
                  AND source_id = %s;
                """,
                (organization_id, source_id),
            )
            return _serialize_source(source, cursor.fetchone())

        status = ACTIVE_SOURCE_STATUS if enabled else NOT_CONFIGURED_SOURCE_STATUS
        cursor.execute(
            """
            UPDATE organization_review_sources
            SET
                is_enabled = %s,
                is_configured = %s,
                status = %s,
                last_error = NULL,
                updated_at = NOW()
            WHERE organization_id = %s
              AND source_id = %s
            RETURNING *;
            """,
            (
                enabled,
                enabled,
                status,
                organization_id,
                source_id,
            ),
        )
        return _serialize_source(source, cursor.fetchone())


def is_source_available(organization_id, source_id):
    sources = list_review_sources(organization_id)
    return any(
        source["source_id"] == source_id
        and source["status"] == ACTIVE_SOURCE_STATUS
        and source["supports_analysis"]
        for source in sources
    )
