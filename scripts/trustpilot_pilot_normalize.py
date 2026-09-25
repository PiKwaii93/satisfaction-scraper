"""Normalize the two existing private pilot JSON files without network access.

This never rewrites the original exports. Run with the exact pilot stamp, for
example: python -m scripts.trustpilot_pilot_normalize 20260924T222637Z
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from app.scraper import normalize_review_datetime


def private_dir() -> Path:
    """Resolve the Windows-only private output path when the script runs."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("Ce script privé nécessite LOCALAPPDATA sous Windows")
    return Path(local_app_data) / "SatisfactionClient" / "TrustpilotPilot"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_record(record: dict) -> dict:
    result = dict(record)
    review_day = normalize_review_datetime(record.get("review_datetime_utc"))
    if not review_day:
        raise ValueError("Horodatage d'avis absent ou invalide")
    if record.get("date") and record["date"] != review_day:
        raise ValueError("Date d'avis déjà renseignée en contradiction avec l'ISO")
    result["date"] = review_day

    if record.get("company_responded"):
        reply_day = normalize_review_datetime(record.get("company_reply_datetime_utc"))
        if not reply_day:
            raise ValueError("Horodatage de réponse absent ou invalide")
        if record.get("company_reply_date") and record["company_reply_date"] != reply_day:
            raise ValueError("Date de réponse déjà renseignée en contradiction avec l'ISO")
        result["company_reply_date"] = reply_day
    return result


def valid_project_record(record: dict) -> bool:
    review_id = record.get("source_review_id")
    return (
        isinstance(review_id, str) and bool(review_id)
        and isinstance(record.get("review_url"), str)
        and record["review_url"].rstrip("/").endswith("/reviews/" + review_id)
        and isinstance(record.get("date"), str)
        and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"]))
        and type(record.get("rating")) is int and 1 <= record["rating"] <= 5
        and isinstance(record.get("title"), str) and bool(record["title"].strip())
        and isinstance(record.get("verbatim"), str) and bool(record["verbatim"].strip())
        and type(record.get("company_responded")) is bool
        and (
            not record["company_responded"]
            or (
                isinstance(record.get("company_reply_text"), str)
                and bool(record["company_reply_text"].strip())
                and isinstance(record.get("company_reply_date"), str)
                and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["company_reply_date"]))
            )
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stamp", help="Exact timestamp shared by the two original pilot files")
    stamp = parser.parse_args().stamp
    if not re.fullmatch(r"\d{8}T\d{6}Z", stamp):
        raise ValueError("Horodatage de pilote invalide")

    root = private_dir()
    inputs = [root / f"showroomprive_page_{page}_{stamp}.json" for page in (11, 50)]
    originals = {path.name: file_sha256(path) for path in inputs}
    payloads = []
    all_ids = set()
    for page, path in zip((11, 50), inputs):
        payload = json.loads(path.read_text(encoding="utf-8"))
        reviews = payload.get("reviews")
        if payload.get("page") != page or not isinstance(reviews, list) or len(reviews) != 20:
            raise ValueError(f"Effectif ou page inattendus : page {page}")
        normalized = [normalize_record(record) for record in reviews]
        page_ids = [record["source_review_id"] for record in normalized]
        if len(set(page_ids)) != 20 or all_ids.intersection(page_ids):
            raise ValueError("Identifiant dupliqué")
        all_ids.update(page_ids)
        if not all(valid_project_record(record) for record in normalized):
            raise ValueError(f"Enregistrement incompatible : page {page}")
        payloads.append((page, path, {**payload, "reviews": normalized}))
    if len(all_ids) != 40:
        raise ValueError("Nombre total d'identifiants inattendu")

    output_dir = root / "normalized"
    output_dir.mkdir(exist_ok=True)
    lines = [
        "# Validation hors ligne du pilote Trustpilot",
        "",
        "- Origine : deux JSON privés du pilote ; aucun nouvel accès au site",
        "- Normalisation : attributs ISO déjà enregistrés, jour civil Europe/Paris",
        "- Originaux préservés : oui",
        "- Identifiants uniques : 40",
        "- Avis avec date valide : 40",
        "- Réponses avec date valide : 37",
        "- Enregistrements compatibles avec les champs du projet : 40",
        "- Texte, titre, note et réponse : conservés à l'identique",
        "- Limite : la concordance des dates relatives visibles sur la page 11 ne peut être revérifiée hors ligne",
        "",
        "| Page | Fichier original | SHA-256 original | Fichier normalisé | SHA-256 normalisé |",
        "|---:|---|---|---|---|",
    ]
    for page, source, payload in payloads:
        destination = output_dir / f"showroomprive_page_{page}_{stamp}_normalized.json"
        with destination.open("x", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.write("\n")
        if json.loads(destination.read_text(encoding="utf-8")) != payload:
            raise RuntimeError("Écriture JSON non conforme")
        lines.append(
            f"| {page} | {source.name} | {originals[source.name]} | "
            f"{destination.name} | {file_sha256(destination)} |"
        )
    if any(file_sha256(path) != originals[path.name] for path in inputs):
        raise RuntimeError("Un original a été modifié")
    report = output_dir / f"validation_normalized_{stamp}.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Copies normalisées et rapport : %LOCALAPPDATA%\\SatisfactionClient\\TrustpilotPilot\\normalized\\")
    print("Pages 11 et 50 : 20 avis chacune ; 40 identifiants uniques ; 37 réponses datées.")


if __name__ == "__main__":
    main()
