import csv
import hashlib
import json
import re
from io import StringIO
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from app.api.database import get_cursor
from app.api.services.insights import build_business_insights, detect_topics
from app.scraper import scrape_trustpilot_by_stars


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_URI = "models:/sentiment_model@production"
ACTIVE_RUN_STATUSES = ("pending", "running")
SENTIMENT_LABELS = {"Positif", "Neutre", "Négatif"}
CSV_SOURCE = "csv"
CSV_MAX_ROWS = 5000
CSV_COLUMN_ALIASES = {
    "verbatim": [
        "verbatim",
        "avis",
        "review",
        "text",
        "texte",
        "comment",
        "commentaire",
        "body",
        "message",
    ],
    "rating": ["rating", "note", "stars", "star", "etoiles", "etoile", "score"],
    "author": ["author", "author_name", "auteur", "nom", "name", "user", "client"],
    "date": ["date", "raw_date", "review_date", "created_at", "published_at"],
    "company_responded": [
        "company_responded",
        "responded",
        "response",
        "reponse",
        "réponse",
        "has_response",
    ],
}
FRENCH_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}


class ActiveAnalysisRunError(ValueError):
    pass


def normalize_sentiment_label(value):
    label = str(value or "").strip().replace("Ã©", "é")
    if label not in SENTIMENT_LABELS:
        raise ValueError("Le label doit etre Positif, Neutre ou Négatif.")
    return label


def normalize_company_slug(value):
    raw_value = value.strip()
    if not raw_value:
        raise ValueError("Le nom ou l'URL de l'entreprise est obligatoire.")

    if raw_value.startswith(("http://", "https://")):
        parsed = urlparse(raw_value)
        if "trustpilot." in parsed.netloc:
            match = re.search(r"/review/([^/?#]+)", parsed.path)
            if not match:
                raise ValueError(f"URL Trustpilot invalide: {raw_value}")
            return match.group(1).strip("/")

        return parsed.netloc.strip("/")

    raw_value = raw_value.replace("https://fr.trustpilot.com/review/", "")
    raw_value = raw_value.replace("http://fr.trustpilot.com/review/", "")
    raw_value = raw_value.split("?")[0].strip("/")

    if "/" in raw_value:
        raw_value = raw_value.rstrip("/").split("/")[-1]

    return raw_value.lower().replace(" ", "-")


def build_trustpilot_url(company_slug):
    return f"https://fr.trustpilot.com/review/{company_slug}"


def safe_file_stem(company_slug):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", company_slug).strip("_")


def default_paths(company_slug, run_id):
    stem = safe_file_stem(company_slug)
    output_dir = PROJECT_ROOT / "data" / "api_runs"
    return (
        output_dir / f"run_{run_id}_{stem}_reviews.json",
        output_dir / f"run_{run_id}_{stem}_predictions.csv",
    )


def normalize_csv_header(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("\ufeff", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def decode_csv_bytes(file_bytes):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Impossible de lire le CSV: encodage non supporte.")


def detect_csv_dialect(csv_text):
    sample = csv_text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        return csv.excel


def resolve_csv_columns(fieldnames):
    normalized_headers = {
        normalize_csv_header(header): header for header in fieldnames or []
    }
    resolved_columns = {}
    missing_columns = []

    for canonical_name, aliases in CSV_COLUMN_ALIASES.items():
        column = next(
            (
                normalized_headers[normalize_csv_header(alias)]
                for alias in aliases
                if normalize_csv_header(alias) in normalized_headers
            ),
            None,
        )
        if column:
            resolved_columns[canonical_name] = column
        elif canonical_name == "verbatim":
            missing_columns.append(canonical_name)

    if missing_columns:
        available = ", ".join(str(header) for header in fieldnames or [])
        raise ValueError(
            "Colonne obligatoire introuvable: verbatim. "
            "Colonnes acceptees: verbatim, avis, review, text, texte, "
            f"commentaire. Colonnes detectees: {available or 'aucune'}."
        )

    return resolved_columns


def parse_boolean_cell(value):
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "oui", "y", "o", "responded", "repondu"}


def normalize_csv_rating(value):
    if value is None or str(value).strip() == "":
        return 3

    match = re.search(r"\d+(?:[,.]\d+)?", str(value))
    if not match:
        return 3

    rating = int(round(float(match.group().replace(",", "."))))
    return min(5, max(1, rating))


def parse_reviews_csv(file_bytes):
    csv_text = decode_csv_bytes(file_bytes)
    if not csv_text.strip():
        raise ValueError("Le fichier CSV est vide.")

    reader = csv.DictReader(StringIO(csv_text), dialect=detect_csv_dialect(csv_text))
    if not reader.fieldnames:
        raise ValueError("Le CSV doit contenir une ligne d'en-tetes.")

    columns = resolve_csv_columns(reader.fieldnames)
    reviews = []
    skipped_rows = 0

    for row_index, row in enumerate(reader, start=2):
        if len(reviews) >= CSV_MAX_ROWS:
            raise ValueError(
                f"CSV trop volumineux: limite actuelle {CSV_MAX_ROWS} avis."
            )

        verbatim = str(row.get(columns["verbatim"], "") or "").strip()
        if not verbatim:
            skipped_rows += 1
            continue

        rating = normalize_csv_rating(row.get(columns.get("rating", ""), 3))
        author = str(row.get(columns.get("author", ""), "") or "").strip()
        raw_date = str(row.get(columns.get("date", ""), "") or "").strip()
        company_responded = parse_boolean_cell(
            row.get(columns.get("company_responded", ""), "")
        )

        reviews.append(
            {
                "author": author or f"CSV #{row_index}",
                "rating": rating,
                "date": raw_date,
                "verbatim": verbatim,
                "company_responded": company_responded,
            }
        )

    if not reviews:
        raise ValueError(
            "Aucun avis exploitable dans le CSV. "
            "Renseigne au moins une ligne avec un verbatim ou une note."
        )

    return {
        "reviews": reviews,
        "skipped_rows": skipped_rows,
        "detected_columns": columns,
    }


def build_csv_import_preview(file_bytes, preview_limit=5):
    parsed_csv = parse_reviews_csv(file_bytes)
    preview_reviews = [
        {
            "row_number": index,
            "rating": review["rating"],
            "author": review["author"],
            "date": review["date"],
            "company_responded": review["company_responded"],
            "verbatim": review["verbatim"],
        }
        for index, review in enumerate(
            parsed_csv["reviews"][:preview_limit],
            start=1,
        )
    ]

    return {
        "review_count": len(parsed_csv["reviews"]),
        "skipped_rows": parsed_csv["skipped_rows"],
        "detected_columns": parsed_csv["detected_columns"],
        "preview_reviews": preview_reviews,
    }


def rating_to_int(raw_rating):
    match = re.search(r"\d+", str(raw_rating))
    return int(match.group()) if match else 3


def parse_review_date(raw_date):
    text = str(raw_date or "").strip().lower()
    match = re.search(r"(\d{1,2})\s+([a-zéû]+)\s+(\d{4})", text)
    if match:
        day = int(match.group(1))
        month = FRENCH_MONTHS.get(match.group(2))
        year = int(match.group(3))
        if month:
            return datetime(year, month, day)

    return parse_relative_review_date(text)


def parse_relative_review_date(date_text):
    now = datetime.now()
    if not date_text:
        return now

    match = re.search(r"\d+", date_text)
    if not match:
        if "jour" in date_text:
            return now - timedelta(days=1)
        if "semaine" in date_text:
            return now - timedelta(weeks=1)
        if "heure" in date_text:
            return now - timedelta(hours=1)
        if "minute" in date_text:
            return now - timedelta(minutes=1)
        return now

    value = int(match.group())
    if "minute" in date_text:
        return now - timedelta(minutes=value)
    if "heure" in date_text:
        return now - timedelta(hours=value)
    if "jour" in date_text:
        return now - timedelta(days=value)
    if "semaine" in date_text:
        return now - timedelta(weeks=value)
    return now


def review_key(review):
    source = "|".join(
        [
            str(review.get("author", "")).strip().lower(),
            str(review.get("rating", "")).strip(),
            str(review.get("date", "")).strip().lower(),
            str(review.get("verbatim", "")).strip().lower(),
        ]
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def parse_stars(stars_requested):
    if isinstance(stars_requested, list):
        return [int(star) for star in stars_requested]
    return [
        int(star.strip())
        for star in str(stars_requested).split(",")
        if star.strip()
    ]


def serialize_run(row):
    if row is None:
        return None

    started_at = row.get("started_at")
    finished_at = row.get("finished_at")
    execution_duration_seconds = None
    if started_at:
        end_at = finished_at or datetime.now()
        execution_duration_seconds = max(
            0,
            int((end_at - started_at).total_seconds()),
        )

    return {
        "run_id": row["run_id"],
        "company_id": row["company_id"],
        "company_name": row["company_name"],
        "trustpilot_slug": row["trustpilot_slug"],
        "source": row["source"],
        "status": row["status"],
        "pages_per_star": row["pages_per_star"],
        "stars_requested": parse_stars(row["stars_requested"]),
        "total_reviews": row["total_reviews"] or 0,
        "celery_task_id": row.get("celery_task_id"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "execution_duration_seconds": execution_duration_seconds,
        "error_message": row.get("error_message"),
    }


def serialize_run_event(row):
    return {
        "event_id": row["event_id"],
        "run_id": row["run_id"],
        "level": row["level"],
        "step": row.get("step"),
        "message": row["message"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def reset_run_events(run_id):
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM analysis_run_events WHERE run_id = %s;",
            (run_id,),
        )


def record_run_event(run_id, message, step=None, level="info"):
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO analysis_run_events (run_id, level, step, message)
            VALUES (%s, %s, %s, %s);
            """,
            (run_id, level, step, message),
        )


def get_run_events(run_id, limit=100):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT event_id, run_id, level, step, message, created_at
            FROM analysis_run_events
            WHERE run_id = %s
            ORDER BY event_id ASC
            LIMIT %s;
            """,
            (run_id, limit),
        )
        return [serialize_run_event(row) for row in cursor.fetchall()]


def get_or_create_company(company_input, source="trustpilot"):
    company_slug = normalize_company_slug(company_input)
    company_name = (
        str(company_input or "").strip()
        if source == CSV_SOURCE
        else company_slug.replace("www.", "")
    )
    source_url = (
        build_trustpilot_url(company_slug)
        if source == "trustpilot"
        else f"{source}://{company_slug}"
    )

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO companies (company_name, trustpilot_slug, source_url, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (trustpilot_slug) DO UPDATE
            SET company_name = EXCLUDED.company_name,
                source_url = EXCLUDED.source_url,
                updated_at = NOW()
            RETURNING company_id, company_name, trustpilot_slug, source_url;
            """,
            (company_name, company_slug, source_url),
        )
        return cursor.fetchone()


def find_active_analysis_run(company_id, source, stars, pages_per_star):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ar.*,
                c.company_name,
                c.trustpilot_slug
            FROM analysis_runs ar
            JOIN companies c ON c.company_id = ar.company_id
            WHERE ar.company_id = %s
              AND ar.source = %s
              AND ar.stars_requested = %s
              AND ar.pages_per_star = %s
              AND ar.status = ANY(%s)
            ORDER BY ar.created_at DESC
            LIMIT 1;
            """,
            (
                company_id,
                source,
                ",".join(str(star) for star in stars),
                pages_per_star,
                list(ACTIVE_RUN_STATUSES),
            ),
        )
        return serialize_run(cursor.fetchone())


def create_analysis_run(request):
    stars = sorted(set(int(star) for star in request.stars))
    invalid_stars = [star for star in stars if star < 1 or star > 5]
    if not stars or invalid_stars:
        raise ValueError("Les notes ciblees doivent etre comprises entre 1 et 5.")

    company = get_or_create_company(request.company)
    active_run = find_active_analysis_run(
        company_id=company["company_id"],
        source=request.source,
        stars=stars,
        pages_per_star=request.pages_per_star,
    )
    if active_run:
        status_label = (
            "en file d'attente"
            if active_run["status"] == "pending"
            else "en cours"
        )
        raise ActiveAnalysisRunError(
            "Une analyse identique est deja "
            f"{status_label} pour {company['company_name']} "
            f"(run #{active_run['run_id']}). "
            "Attends sa fin ou ouvre-la depuis l'historique."
        )

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO analysis_runs (
                company_id, source, status, stars_requested, pages_per_star, model_uri
            )
            VALUES (%s, %s, 'pending', %s, %s, %s)
            RETURNING run_id;
            """,
            (
                company["company_id"],
                request.source,
                ",".join(str(star) for star in stars),
                request.pages_per_star,
                MODEL_URI,
            ),
        )
        run_id = cursor.fetchone()["run_id"]

    if request.execute_immediately:
        queue_analysis_run(run_id, skip_scrape=request.skip_scrape)

    return get_analysis_run(run_id)


def create_csv_analysis_run(company_input, file_bytes, original_filename=None):
    parsed_csv = parse_reviews_csv(file_bytes)
    company = get_or_create_company(company_input, source=CSV_SOURCE)
    active_run = find_active_analysis_run(
        company_id=company["company_id"],
        source=CSV_SOURCE,
        stars=[],
        pages_per_star=1,
    )
    if active_run:
        status_label = (
            "en file d'attente"
            if active_run["status"] == "pending"
            else "en cours"
        )
        raise ActiveAnalysisRunError(
            "Un import CSV est deja "
            f"{status_label} pour {company['company_name']} "
            f"(run #{active_run['run_id']})."
        )

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO analysis_runs (
                company_id, source, status, stars_requested, pages_per_star, model_uri
            )
            VALUES (%s, %s, 'pending', %s, %s, %s)
            RETURNING run_id;
            """,
            (
                company["company_id"],
                CSV_SOURCE,
                "",
                1,
                MODEL_URI,
            ),
        )
        run_id = cursor.fetchone()["run_id"]

    json_path, csv_path = default_paths(company["trustpilot_slug"], run_id)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "target_company": company["company_name"],
        "source": CSV_SOURCE,
        "original_filename": original_filename,
        "detected_columns": parsed_csv["detected_columns"],
        "skipped_rows": parsed_csv["skipped_rows"],
        "reviews": parsed_csv["reviews"],
    }
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE analysis_runs
            SET reviews_json_path = %s,
                predictions_csv_path = %s,
                updated_at = NOW()
            WHERE run_id = %s;
            """,
            (str(json_path), str(csv_path), run_id),
        )

    queue_analysis_run(run_id, skip_scrape=True)
    record_run_event(
        run_id,
        f"CSV importe: {len(parsed_csv['reviews'])} avis exploitables.",
        step="csv_import",
    )
    if parsed_csv["skipped_rows"]:
        record_run_event(
            run_id,
            f"{parsed_csv['skipped_rows']} ligne(s) CSV ignoree(s).",
            step="csv_import",
            level="warning",
        )

    return get_analysis_run(run_id)


def queue_analysis_run(run_id, skip_scrape=False):
    from app.api.services.job_queue import enqueue_analysis_run

    task_id = f"analysis-run-{run_id}"
    reset_run_events(run_id)

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE analysis_runs
            SET status = 'pending',
                celery_task_id = %s,
                total_reviews = 0,
                error_message = NULL,
                started_at = NULL,
                finished_at = NULL,
                updated_at = NOW()
            WHERE run_id = %s;
            """,
            (task_id, run_id),
        )

    record_run_event(
        run_id,
        "Analyse placee dans la file d'attente.",
        step="queued",
    )
    enqueue_analysis_run(run_id, skip_scrape=skip_scrape, task_id=task_id)
    record_run_event(
        run_id,
        f"Tache Celery envoyee: {task_id}.",
        step="queued",
    )

    return task_id


def get_analysis_run(run_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ar.*,
                c.company_name,
                c.trustpilot_slug
            FROM analysis_runs ar
            JOIN companies c ON c.company_id = ar.company_id
            WHERE ar.run_id = %s;
            """,
            (run_id,),
        )
        return serialize_run(cursor.fetchone())


def list_analysis_runs(limit=50, offset=0):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ar.*,
                c.company_name,
                c.trustpilot_slug
            FROM analysis_runs ar
            JOIN companies c ON c.company_id = ar.company_id
            ORDER BY ar.created_at DESC
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        return [serialize_run(row) for row in cursor.fetchall()]


def execute_analysis_run(run_id, skip_scrape=False):
    run = get_analysis_run(run_id)
    if run is None:
        raise ValueError(f"Analyse introuvable: {run_id}")

    record_run_event(
        run_id,
        "Le worker demarre l'analyse.",
        step="worker_start",
    )

    company_slug = run["trustpilot_slug"]
    stars = run["stars_requested"]
    json_path, csv_path = default_paths(company_slug, run_id)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE analysis_runs
            SET status = 'running',
                started_at = NOW(),
                updated_at = NOW(),
                error_message = NULL,
                reviews_json_path = %s,
                predictions_csv_path = %s
            WHERE run_id = %s;
            """,
            (str(json_path), str(csv_path), run_id),
        )

    try:
        record_run_event(
            run_id,
            "Preparation des chemins de sortie.",
            step="prepare_outputs",
        )

        if run["source"] == CSV_SOURCE:
            if not json_path.exists():
                raise FileNotFoundError(f"JSON introuvable pour ce run: {json_path}")
            record_run_event(
                run_id,
                "Import CSV detecte, lecture du JSON normalise.",
                step="csv_load",
            )
        elif not skip_scrape:
            record_run_event(
                run_id,
                f"Scraping Trustpilot demarre pour {company_slug}.",
                step="scrape_start",
            )

            def record_scrape_progress(step, message, level="info"):
                record_run_event(run_id, message, step=step, level=level)

            scrape_trustpilot_by_stars(
                company_slug=company_slug,
                output_path=str(json_path),
                stars_list=stars,
                pages_per_star=run["pages_per_star"],
                progress_callback=record_scrape_progress,
            )
            record_run_event(
                run_id,
                "Scraping Trustpilot termine.",
                step="scrape_complete",
            )
        elif not json_path.exists():
            raise FileNotFoundError(f"JSON introuvable pour ce run: {json_path}")
        else:
            record_run_event(
                run_id,
                "Scraping ignore, reutilisation du JSON existant.",
                step="scrape_skipped",
            )

        record_run_event(
            run_id,
            "Lecture des avis extraits.",
            step="load_reviews",
        )
        with json_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        review_count = len(payload.get("reviews", []))
        record_run_event(
            run_id,
            f"{review_count} avis charges depuis le fichier JSON.",
            step="load_reviews",
        )

        if review_count == 0:
            message = (
                "Aucun avis exploitable n'a ete trouve dans le CSV importe."
                if run["source"] == CSV_SOURCE
                else (
                    "Aucun avis n'a ete recupere pour cette analyse. "
                    "Verifie l'URL Trustpilot, les filtres d'etoiles ou le nombre "
                    "de pages demande."
                )
            )
            with get_cursor(commit=True) as cursor:
                cursor.execute(
                    """
                    UPDATE analysis_runs
                    SET status = 'empty',
                        total_reviews = 0,
                        finished_at = NOW(),
                        updated_at = NOW(),
                        error_message = %s
                    WHERE run_id = %s;
                    """,
                    (message, run_id),
                )
            record_run_event(
                run_id,
                message,
                step="no_reviews",
                level="warning",
            )
            return get_analysis_run(run_id)

        record_run_event(
            run_id,
            "Predictions IA et sauvegarde en base.",
            step="predict",
        )
        rows = persist_reviews(
            run_id=run_id,
            company_id=run["company_id"],
            payload=payload,
        )
        record_run_event(
            run_id,
            f"{len(rows)} avis analyses et enregistres.",
            step="persist_reviews",
        )
        write_predictions_csv(csv_path, payload.get("target_company", company_slug), rows)
        record_run_event(
            run_id,
            "Export CSV genere.",
            step="export",
        )

        with get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE analysis_runs
                SET status = 'completed',
                    total_reviews = %s,
                    finished_at = NOW(),
                    updated_at = NOW(),
                    error_message = NULL
                WHERE run_id = %s;
                """,
                (len(rows), run_id),
            )

        record_run_event(
            run_id,
            "Analyse terminee avec succes.",
            step="completed",
        )
        return get_analysis_run(run_id)

    except Exception as exc:
        with get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                UPDATE analysis_runs
                SET status = 'failed',
                    error_message = %s,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE run_id = %s;
                """,
                (str(exc), run_id),
            )
        record_run_event(
            run_id,
            f"Analyse echouee: {exc}",
            step="failed",
            level="error",
        )
        raise


def persist_reviews(run_id, company_id, payload):
    from app.sentiment_analysis import get_sentiment

    persisted_rows = []
    reviews = payload.get("reviews", [])

    with get_cursor(commit=True) as cursor:
        for review in reviews:
            rating = rating_to_int(review.get("rating", 3))
            verbatim = str(review.get("verbatim") or "").strip()
            label, score = get_sentiment(verbatim, rating)
            topics = detect_topics(verbatim)

            cursor.execute(
                """
                INSERT INTO reviews (
                    run_id, company_id, external_review_key, author_name, rating,
                    raw_date, review_date, verbatim, company_responded
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, external_review_key) DO UPDATE
                SET author_name = EXCLUDED.author_name,
                    rating = EXCLUDED.rating,
                    raw_date = EXCLUDED.raw_date,
                    review_date = EXCLUDED.review_date,
                    verbatim = EXCLUDED.verbatim,
                    company_responded = EXCLUDED.company_responded
                RETURNING review_id;
                """,
                (
                    run_id,
                    company_id,
                    review_key(review),
                    review.get("author", ""),
                    rating,
                    review.get("date", ""),
                    parse_review_date(review.get("date", "")),
                    verbatim,
                    bool(review.get("company_responded", False)),
                ),
            )
            review_id = cursor.fetchone()["review_id"]

            cursor.execute(
                """
                INSERT INTO sentiment_predictions (review_id, label, score, model_uri)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (review_id) DO UPDATE
                SET label = EXCLUDED.label,
                    score = EXCLUDED.score,
                    model_uri = EXCLUDED.model_uri,
                    created_at = NOW();
                """,
                (review_id, label, score, MODEL_URI),
            )

            cursor.execute(
                "DELETE FROM review_topics WHERE review_id = %s;",
                (review_id,),
            )

            for topic in topics:
                cursor.execute(
                    """
                    INSERT INTO review_topics (review_id, topic)
                    VALUES (%s, %s)
                    ON CONFLICT (review_id, topic) DO NOTHING;
                    """,
                    (review_id, topic),
                )

            persisted_rows.append(
                {
                    "review_id": review_id,
                    "author": review.get("author", ""),
                    "rating": rating,
                    "date": review.get("date", ""),
                    "sentiment_label": label,
                    "sentiment_score": score,
                    "company_responded": bool(review.get("company_responded", False)),
                    "topics": topics,
                    "verbatim": verbatim,
                }
            )

    return persisted_rows


def write_predictions_csv(csv_path, target_company, rows):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "review_id",
                "target_company",
                "author",
                "rating",
                "date",
                "sentiment_label",
                "sentiment_score",
                "company_responded",
                "topics",
                "verbatim",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "target_company": target_company,
                    "topics": ",".join(row.get("topics", [])),
                }
            )


def get_run_reviews(run_id, sentiment=None, limit=100, offset=0):
    filters = ["r.run_id = %s"]
    params = [run_id]
    if sentiment:
        filters.append("sp.label = %s")
        params.append(sentiment)

    params.extend([limit, offset])

    with get_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                r.review_id,
                r.rating,
                r.author_name,
                r.raw_date,
                r.verbatim,
                r.company_responded,
                sp.label AS sentiment_label,
                sp.score AS sentiment_score,
                rf.corrected_label,
                rf.comment AS feedback_comment,
                rf.updated_at AS feedback_updated_at,
                COALESCE(
                    ARRAY_REMOVE(ARRAY_AGG(rt.topic ORDER BY rt.topic), NULL),
                    ARRAY[]::varchar[]
                ) AS topics
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            LEFT JOIN review_feedback rf ON rf.review_id = r.review_id
            LEFT JOIN review_topics rt ON rt.review_id = r.review_id
            WHERE {" AND ".join(filters)}
            GROUP BY r.review_id, sp.label, sp.score, rf.corrected_label, rf.comment, rf.updated_at
            ORDER BY r.review_id
            LIMIT %s OFFSET %s;
            """,
            params,
        )
        rows = cursor.fetchall()

        count_params = params[:-2]
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            WHERE {" AND ".join(filters)};
            """,
            count_params,
        )
        total = cursor.fetchone()["total"]

    return {
        "run_id": run_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "reviews": [dict(row) for row in rows],
    }


def save_review_feedback(run_id, review_id, payload):
    corrected_label = normalize_sentiment_label(payload.corrected_label)
    comment = (payload.comment or "").strip() or None

    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT
                r.review_id,
                r.run_id,
                sp.label AS predicted_label
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            WHERE r.run_id = %s AND r.review_id = %s;
            """,
            (run_id, review_id),
        )
        review = cursor.fetchone()
        if review is None:
            return None

        cursor.execute(
            """
            INSERT INTO review_feedback (
                review_id, predicted_label, corrected_label, comment
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (review_id) DO UPDATE
            SET predicted_label = EXCLUDED.predicted_label,
                corrected_label = EXCLUDED.corrected_label,
                comment = EXCLUDED.comment,
                updated_at = NOW()
            RETURNING
                feedback_id,
                review_id,
                predicted_label,
                corrected_label,
                comment,
                created_at,
                updated_at;
            """,
            (review_id, review["predicted_label"], corrected_label, comment),
        )
        feedback = dict(cursor.fetchone())
        feedback["run_id"] = run_id
        return feedback


def delete_review_feedback(run_id, review_id):
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            DELETE FROM review_feedback rf
            USING reviews r
            WHERE rf.review_id = r.review_id
              AND r.run_id = %s
              AND r.review_id = %s
            RETURNING rf.feedback_id;
            """,
            (run_id, review_id),
        )
        return cursor.fetchone() is not None


def get_run_summary(run_id):
    run = get_analysis_run(run_id)
    if run is None:
        return None

    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS review_count,
                AVG(r.rating) AS average_rating,
                AVG(sp.score) AS average_confidence,
                SUM(CASE WHEN r.company_responded THEN 1 ELSE 0 END) AS responded_count,
                SUM(CASE WHEN COALESCE(r.verbatim, '') <> '' THEN 1 ELSE 0 END) AS text_count,
                COUNT(rf.feedback_id) AS feedback_count
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            LEFT JOIN review_feedback rf ON rf.review_id = r.review_id
            WHERE r.run_id = %s;
            """,
            (run_id,),
        )
        kpis = dict(cursor.fetchone())

        cursor.execute(
            """
            SELECT sp.label, COUNT(*) AS count
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            WHERE r.run_id = %s
            GROUP BY sp.label
            ORDER BY sp.label;
            """,
            (run_id,),
        )
        sentiment_distribution = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT r.rating, COUNT(*) AS count
            FROM reviews r
            WHERE r.run_id = %s
            GROUP BY r.rating
            ORDER BY r.rating;
            """,
            (run_id,),
        )
        rating_distribution = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT rt.topic, COUNT(*) AS count
            FROM reviews r
            JOIN review_topics rt ON rt.review_id = r.review_id
            WHERE r.run_id = %s
            GROUP BY rt.topic
            ORDER BY count DESC, rt.topic
            LIMIT 10;
            """,
            (run_id,),
        )
        top_topics = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                r.review_id,
                r.rating,
                r.author_name,
                r.verbatim,
                sp.label AS sentiment_label,
                sp.score AS sentiment_score
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            WHERE r.run_id = %s
              AND sp.label = 'Négatif'
              AND COALESCE(r.verbatim, '') <> ''
            ORDER BY r.rating ASC NULLS LAST, sp.score DESC
            LIMIT 10;
            """,
            (run_id,),
        )
        critical_reviews = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                r.review_id,
                r.rating,
                r.author_name,
                r.verbatim,
                sp.label AS sentiment_label,
                sp.score AS sentiment_score
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            WHERE r.run_id = %s
              AND (
                (r.rating >= 4 AND sp.label = 'Négatif')
                OR (r.rating <= 2 AND sp.label = 'Positif')
              )
            ORDER BY r.rating DESC, sp.score DESC
            LIMIT 10;
            """,
            (run_id,),
        )
        rating_text_mismatches = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                rt.topic,
                sp.label AS sentiment_label,
                COUNT(*) AS count
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            JOIN review_topics rt ON rt.review_id = r.review_id
            WHERE r.run_id = %s
            GROUP BY rt.topic, sp.label
            ORDER BY count DESC, rt.topic;
            """,
            (run_id,),
        )
        topic_sentiment_distribution = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                rt.topic,
                r.review_id,
                r.rating,
                r.verbatim,
                sp.label AS sentiment_label,
                sp.score AS sentiment_score
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            JOIN review_topics rt ON rt.review_id = r.review_id
            WHERE r.run_id = %s
              AND sp.label = 'Négatif'
              AND COALESCE(r.verbatim, '') <> ''
            ORDER BY rt.topic, r.rating ASC NULLS LAST, sp.score DESC
            LIMIT 80;
            """,
            (run_id,),
        )
        negative_topic_examples = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                rt.topic,
                r.review_id,
                r.rating,
                r.verbatim,
                sp.label AS sentiment_label,
                sp.score AS sentiment_score
            FROM reviews r
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            JOIN review_topics rt ON rt.review_id = r.review_id
            WHERE r.run_id = %s
              AND sp.label = 'Positif'
              AND COALESCE(r.verbatim, '') <> ''
            ORDER BY rt.topic, sp.score DESC, r.rating DESC NULLS LAST
            LIMIT 80;
            """,
            (run_id,),
        )
        positive_topic_examples = [dict(row) for row in cursor.fetchall()]

    business_insights = build_business_insights(
        kpis=kpis,
        sentiment_distribution=sentiment_distribution,
        topic_sentiment_distribution=topic_sentiment_distribution,
        negative_topic_examples=negative_topic_examples,
        positive_topic_examples=positive_topic_examples,
        critical_reviews=critical_reviews,
        rating_text_mismatches=rating_text_mismatches,
    )

    return {
        "run": run,
        "kpis": kpis,
        "sentiment_distribution": sentiment_distribution,
        "rating_distribution": rating_distribution,
        "top_topics": top_topics,
        "critical_reviews": critical_reviews,
        "rating_text_mismatches": rating_text_mismatches,
        "business_insights": business_insights,
    }


def normalize_label(value):
    return str(value or "").replace("Ã©", "é")


def get_distribution_count(rows, key, field="label"):
    normalized_key = normalize_label(key)
    for row in rows:
        if normalize_label(row.get(field)) == normalized_key:
            return int(row.get("count") or 0)
    return 0


def as_float(value):
    return None if value is None else float(value)


def percentage(part, total):
    if not total:
        return 0.0
    return round((part / total) * 100, 1)


def build_benchmark_company(summary):
    run = summary["run"]
    kpis = summary["kpis"]
    review_count = int(kpis.get("review_count") or 0)
    negative_count = get_distribution_count(
        summary["sentiment_distribution"],
        "Négatif",
    )
    neutral_count = get_distribution_count(
        summary["sentiment_distribution"],
        "Neutre",
    )
    positive_count = get_distribution_count(
        summary["sentiment_distribution"],
        "Positif",
    )

    return {
        "run_id": run["run_id"],
        "company_name": run["company_name"],
        "review_count": review_count,
        "text_count": int(kpis.get("text_count") or 0),
        "average_rating": as_float(kpis.get("average_rating")),
        "average_confidence": as_float(kpis.get("average_confidence")),
        "health_score": int(summary["business_insights"]["health_score"]),
        "risk_level": summary["business_insights"]["risk_level"],
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "positive_count": positive_count,
        "negative_rate": percentage(negative_count, review_count),
        "top_topics": [
            {
                "topic": row.get("topic") or "Sujet",
                "count": int(row.get("count") or 0),
            }
            for row in summary["top_topics"][:5]
        ],
        "unique_topics": [],
    }


def get_runs_comparison(run_ids):
    unique_run_ids = []
    for run_id in run_ids:
        if run_id not in unique_run_ids:
            unique_run_ids.append(run_id)

    if len(unique_run_ids) < 2 or len(unique_run_ids) > 4:
        raise ValueError("Selectionne entre 2 et 4 analyses a comparer.")

    summaries = []
    for run_id in unique_run_ids:
        summary = get_run_summary(run_id)
        if summary is None:
            raise ValueError(f"Analyse introuvable: {run_id}")
        if summary["run"]["status"] != "completed":
            raise ValueError(
                "Seules les analyses terminees peuvent etre comparees "
                f"(run #{run_id})."
            )
        summaries.append(summary)

    companies = [build_benchmark_company(summary) for summary in summaries]
    topic_index = {}
    for company in companies:
        for topic in company["top_topics"]:
            entry = {
                "run_id": company["run_id"],
                "company_name": company["company_name"],
                "count": topic["count"],
            }
            topic_index.setdefault(topic["topic"], []).append(entry)

    common_topics = []
    for topic, entries in topic_index.items():
        if len(entries) < 2:
            continue
        common_topics.append(
            {
                "topic": topic,
                "total_count": sum(entry["count"] for entry in entries),
                "run_count": len(entries),
                "companies": sorted(
                    entries,
                    key=lambda item: (-item["count"], item["company_name"]),
                ),
            }
        )

    common_topics = sorted(
        common_topics,
        key=lambda item: (-item["total_count"], item["topic"]),
    )[:8]
    common_topic_names = {topic["topic"] for topic in common_topics}

    for company in companies:
        company["unique_topics"] = [
            topic
            for topic in company["top_topics"]
            if topic["topic"] not in common_topic_names
        ][:3]

    highlights = {
        "best_health": max(
            companies,
            key=lambda item: (item["health_score"], item["average_rating"] or 0),
        ),
        "highest_negative_rate": max(
            companies,
            key=lambda item: (item["negative_rate"], item["negative_count"]),
        ),
        "most_reviews": max(
            companies,
            key=lambda item: item["review_count"],
        ),
        "shared_priority": common_topics[0] if common_topics else None,
    }

    return {
        "run_ids": unique_run_ids,
        "companies": companies,
        "common_topics": common_topics,
        "highlights": highlights,
    }


def get_feedback_export_rows(run_id):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                r.review_id,
                r.run_id,
                c.company_name,
                r.rating,
                r.author_name,
                r.raw_date,
                sp.label AS predicted_label,
                rf.corrected_label,
                sp.score AS sentiment_score,
                rf.comment AS feedback_comment,
                rf.updated_at AS feedback_updated_at,
                r.verbatim,
                COALESCE(
                    ARRAY_REMOVE(ARRAY_AGG(rt.topic ORDER BY rt.topic), NULL),
                    ARRAY[]::varchar[]
                ) AS topics
            FROM review_feedback rf
            JOIN reviews r ON r.review_id = rf.review_id
            JOIN companies c ON c.company_id = r.company_id
            JOIN sentiment_predictions sp ON sp.review_id = r.review_id
            LEFT JOIN review_topics rt ON rt.review_id = r.review_id
            WHERE r.run_id = %s
            GROUP BY
                r.review_id,
                c.company_name,
                sp.label,
                sp.score,
                rf.corrected_label,
                rf.comment,
                rf.updated_at
            ORDER BY rf.updated_at DESC, r.review_id;
            """,
            (run_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_feedback_quality_summary(recent_limit=8):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_corrections,
                COALESCE(
                    SUM(
                        CASE
                            WHEN REPLACE(rf.corrected_label, 'Ã©', 'é')
                                <> REPLACE(rf.predicted_label, 'Ã©', 'é')
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS changed_label_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN REPLACE(rf.corrected_label, 'Ã©', 'é')
                                = REPLACE(rf.predicted_label, 'Ã©', 'é')
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS confirmed_label_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN COALESCE(r.verbatim, '') <> '' THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS training_ready_count,
                COUNT(DISTINCT c.company_id) AS corrected_company_count,
                COUNT(DISTINCT r.run_id) AS corrected_run_count,
                MAX(rf.updated_at) AS latest_feedback_at
            FROM review_feedback rf
            JOIN reviews r ON r.review_id = rf.review_id
            JOIN companies c ON c.company_id = r.company_id;
            """
        )
        summary = dict(cursor.fetchone())

        total_corrections = int(summary["total_corrections"] or 0)
        changed_label_count = int(summary["changed_label_count"] or 0)
        apparent_error_rate = percentage(changed_label_count, total_corrections)

        cursor.execute(
            """
            SELECT
                c.company_id,
                c.company_name,
                COUNT(*) AS correction_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN REPLACE(rf.corrected_label, 'Ã©', 'é')
                                <> REPLACE(rf.predicted_label, 'Ã©', 'é')
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS changed_label_count,
                COUNT(DISTINCT r.run_id) AS run_count,
                MAX(rf.updated_at) AS latest_feedback_at
            FROM review_feedback rf
            JOIN reviews r ON r.review_id = rf.review_id
            JOIN companies c ON c.company_id = r.company_id
            GROUP BY c.company_id, c.company_name
            ORDER BY correction_count DESC, latest_feedback_at DESC
            LIMIT 8;
            """
        )
        by_company = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT REPLACE(corrected_label, 'Ã©', 'é') AS label, COUNT(*) AS count
            FROM review_feedback
            GROUP BY REPLACE(corrected_label, 'Ã©', 'é')
            ORDER BY count DESC, label;
            """
        )
        corrected_label_distribution = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                REPLACE(predicted_label, 'Ã©', 'é') AS predicted_label,
                REPLACE(corrected_label, 'Ã©', 'é') AS corrected_label,
                COUNT(*) AS count
            FROM review_feedback
            GROUP BY
                REPLACE(predicted_label, 'Ã©', 'é'),
                REPLACE(corrected_label, 'Ã©', 'é')
            ORDER BY count DESC, predicted_label, corrected_label;
            """
        )
        transitions = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT
                rf.feedback_id,
                r.review_id,
                r.run_id,
                c.company_name,
                r.rating,
                REPLACE(rf.predicted_label, 'Ã©', 'é') AS predicted_label,
                REPLACE(rf.corrected_label, 'Ã©', 'é') AS corrected_label,
                rf.comment AS feedback_comment,
                rf.updated_at AS feedback_updated_at,
                r.verbatim
            FROM review_feedback rf
            JOIN reviews r ON r.review_id = rf.review_id
            JOIN companies c ON c.company_id = r.company_id
            ORDER BY rf.updated_at DESC, rf.feedback_id DESC
            LIMIT %s;
            """,
            (recent_limit,),
        )
        recent_corrections = [dict(row) for row in cursor.fetchall()]

    return {
        "total_corrections": total_corrections,
        "changed_label_count": changed_label_count,
        "confirmed_label_count": int(summary["confirmed_label_count"] or 0),
        "apparent_error_rate": apparent_error_rate,
        "training_ready_count": int(summary["training_ready_count"] or 0),
        "corrected_company_count": int(summary["corrected_company_count"] or 0),
        "corrected_run_count": int(summary["corrected_run_count"] or 0),
        "latest_feedback_at": summary["latest_feedback_at"],
        "by_company": by_company,
        "corrected_label_distribution": corrected_label_distribution,
        "transitions": transitions,
        "recent_corrections": recent_corrections,
    }


def get_export_rows(run_id):
    return get_run_reviews(run_id, limit=10000, offset=0)["reviews"]
