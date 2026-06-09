import argparse
import csv
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from app.sentiment_analysis import get_sentiment

try:
    from app.etl import run_etl
    from app.scraper import scrape_trustpilot_by_stars
except ImportError:
    from etl import run_etl
    from scraper import scrape_trustpilot_by_stars


PROJECT_ROOT = Path("/app")
DEFAULT_COMPANY_URL = "https://fr.trustpilot.com/review/labonneallure.fr"


def parse_stars(value):
    return [int(star.strip()) for star in value.split(",") if star.strip()]


def normalize_company_slug(value):
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        match = re.search(r"/review/([^/?#]+)", parsed.path)
        if not match:
            raise ValueError(f"URL Trustpilot invalide: {value}")
        return match.group(1)

    return value.replace("https://fr.trustpilot.com/review/", "").strip("/")


def safe_file_stem(company_slug):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", company_slug).strip("_")


def default_paths(company_slug):
    stem = safe_file_stem(company_slug)
    external_dir = PROJECT_ROOT / "data" / "external"
    return (
        external_dir / f"{stem}_reviews.json",
        external_dir / f"{stem}_predictions.csv",
    )


def rating_to_int(raw_rating):
    match = re.search(r"\d+", str(raw_rating))
    return int(match.group()) if match else 3


def predict_reviews(json_path, csv_path):
    with Path(json_path).open("r", encoding="utf-8") as file:
        payload = json.load(file)

    rows = []
    for review_id, review in enumerate(payload.get("reviews", [])):
        rating = rating_to_int(review.get("rating", 3))
        verbatim = str(review.get("verbatim") or "").strip()
        label, score = get_sentiment(verbatim, rating)

        rows.append(
            {
                "id": review_id,
                "target_company": payload.get("target_company", ""),
                "author": review.get("author", ""),
                "rating": rating,
                "date": review.get("date", ""),
                "sentiment_label": label,
                "sentiment_score": score,
                "company_responded": review.get("company_responded", False),
                "verbatim": verbatim,
            }
        )

    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "target_company",
                "author",
                "rating",
                "date",
                "sentiment_label",
                "sentiment_score",
                "company_responded",
                "verbatim",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] CSV de prédictions généré: {csv_path} ({len(rows)} lignes)")
    return rows


def truncate_fact_reviews():
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123"),
    )
    try:
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE fact_reviews RESTART IDENTITY;")
        conn.commit()
        cursor.close()
        print("[+] Table fact_reviews vidée pour afficher seulement le test externe.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Scrape une entreprise Trustpilot externe et prédit les sentiments sans réentraîner le modèle."
    )
    parser.add_argument("--company", default=DEFAULT_COMPANY_URL)
    parser.add_argument("--stars", default=os.getenv("TRUSTPILOT_STARS", "1,2,3,4,5"))
    parser.add_argument(
        "--pages-per-star",
        type=int,
        default=int(os.getenv("PAGES_PER_STAR", "2")),
    )
    parser.add_argument("--json-path")
    parser.add_argument("--csv-path")
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Réutilise le JSON existant et régénère seulement le CSV de prédictions.",
    )
    parser.add_argument(
        "--sync-db",
        action="store_true",
        help="Charge aussi les avis externes dans PostgreSQL pour les afficher dans le dashboard.",
    )
    parser.add_argument(
        "--replace-db",
        action="store_true",
        help="Vide fact_reviews avant --sync-db pour afficher uniquement cette entreprise.",
    )
    args = parser.parse_args()

    company_slug = normalize_company_slug(args.company)
    default_json_path, default_csv_path = default_paths(company_slug)
    json_path = Path(args.json_path) if args.json_path else default_json_path
    csv_path = Path(args.csv_path) if args.csv_path else default_csv_path

    if not args.skip_scrape:
        scrape_trustpilot_by_stars(
            company_slug=company_slug,
            output_path=str(json_path),
            stars_list=parse_stars(args.stars),
            pages_per_star=args.pages_per_star,
        )
    elif not json_path.exists():
        raise FileNotFoundError(f"JSON introuvable pour --skip-scrape: {json_path}")

    predict_reviews(json_path, csv_path)

    if args.sync_db:
        if args.replace_db:
            truncate_fact_reviews()
        run_etl(str(json_path))


if __name__ == "__main__":
    main()
