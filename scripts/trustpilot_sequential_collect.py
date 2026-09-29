"""Sequential Trustpilot pilot extension over an existing, manually authenticated CDP browser.

No browser is launched here. A live run requires --execute; --dry-run never connects.
Only use this with authorization to collect and reuse the target reviews.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.scraper import REVIEW_CARD_SELECTOR, extract_reviews_from_page, review_identity_from_card
from scripts.trustpilot_manual_check import connect_existing_browser, is_challenge

MAX_PAGES = 40
MANIFEST_NAME = "manifest.json"
PRIVATE_REVIEW_FIELDS = (
    "source_review_id", "review_url", "rating", "date", "title", "verbatim",
    "company_responded", "company_reply_text", "company_reply_date",
)


class CollectionStopped(RuntimeError):
    """A page could not be fully validated; no subsequent page may be requested."""


@dataclass(frozen=True)
class Config:
    company: str
    start_page: int
    end_page: int
    output_dir: Path
    resume: bool = False

    def validate(self):
        if not re.fullmatch(r"[A-Za-z0-9.-]+", self.company) or ".." in self.company:
            raise ValueError("Invalid company domain")
        if self.start_page < 1 or self.end_page < self.start_page:
            raise ValueError("Invalid page range")
        if self.end_page - self.start_page + 1 > MAX_PAGES:
            raise ValueError(f"At most {MAX_PAGES} pages per run")

    def url(self, number):
        return f"https://fr.trustpilot.com/review/{self.company}?page={number}"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_write(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".page-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def page_name(number):
    return f"page_{number:04d}.json"


def validate_review(review):
    review_id = review.get("source_review_id")
    parsed = urlparse(str(review.get("review_url") or ""))
    if not review_id or parsed.hostname != "fr.trustpilot.com" or parsed.path != f"/reviews/{review_id}":
        raise CollectionStopped("Missing or inconsistent stable review ID")
    if type(review.get("rating")) is not int or review["rating"] not in range(1, 6):
        raise CollectionStopped("Missing or invalid rating")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review["date"]):
            raise ValueError
        date.fromisoformat(review["date"])
    except (KeyError, TypeError, ValueError):
        raise CollectionStopped("Missing or invalid review date") from None
    if not str(review.get("title") or "").strip() or not str(review.get("verbatim") or "").strip():
        raise CollectionStopped("Missing review title or text")
    if review.get("company_responded"):
        if not str(review.get("company_reply_text") or "").strip():
            raise CollectionStopped("Missing business reply text")
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review["company_reply_date"]):
                raise ValueError
            date.fromisoformat(review["company_reply_date"])
        except (KeyError, TypeError, ValueError):
            raise CollectionStopped("Missing or invalid business reply date") from None
    elif review.get("company_reply_text") or review.get("company_reply_date"):
        raise CollectionStopped("Inconsistent business reply")


def validate_capture(config, number, capture):
    if capture["status"] in (403, 429):
        raise CollectionStopped(f"HTTP {capture['status']}")
    if capture["status"] != 200:
        raise CollectionStopped(f"Unexpected HTTP {capture['status']}")
    if capture.get("challenge"):
        raise CollectionStopped("CAPTCHA or verification page")
    if capture.get("redirected") or capture["url"] != config.url(number):
        raise CollectionStopped("Redirect or unexpected final URL")
    ids = capture["card_ids"]
    reviews = capture["reviews"]
    if capture["card_count"] < len(ids) or not ids or len(set(ids)) != len(ids):
        raise CollectionStopped("Empty page or duplicate stable IDs within page")
    if len(reviews) != len(ids) or {r.get("source_review_id") for r in reviews} != set(ids):
        raise CollectionStopped("Some visible review cards were not completely parsed")
    for review in reviews:
        validate_review(review)


def _load_existing(config):
    manifest_path = config.output_dir / MANIFEST_NAME
    if not config.resume:
        if manifest_path.exists() or any(config.output_dir.glob("page_*.json")):
            raise CollectionStopped("Output already contains a collection; use --resume")
        return {"company": config.company, "start_page": config.start_page,
                "end_page": config.end_page, "created_at": utc_now(), "pages": {},
                "unique_review_ids": [], "last_error": None}
    if not manifest_path.exists():
        raise CollectionStopped("No manifest to resume")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if any(manifest.get(key) != value for key, value in
           (("company", config.company), ("start_page", config.start_page), ("end_page", config.end_page))):
        raise CollectionStopped("Manifest configuration mismatch")
    seen = set()
    for number in range(config.start_page, config.end_page + 1):
        path = config.output_dir / page_name(number)
        record = manifest["pages"].get(str(number))
        if not path.exists():
            if record:
                raise CollectionStopped("Manifest references a missing page file")
            if any((config.output_dir / page_name(later)).exists()
                   for later in range(number + 1, config.end_page + 1)):
                raise CollectionStopped("Non-contiguous page files")
            break
        raw = path.read_bytes()
        page = json.loads(raw)
        if page.get("page") != number or page.get("company") != config.company:
            raise CollectionStopped("Saved page identity mismatch")
        if page.get("status") != 200 or not page.get("card_ids"):
            raise CollectionStopped("Saved page is incomplete")
        ids = page["card_ids"]
        if len(ids) != len(set(ids)) or page.get("valid_count") != len(ids):
            raise CollectionStopped("Saved page counts are inconsistent")
        if set(page.get("new_review_ids", [])) != {r.get("source_review_id") for r in page.get("reviews", [])}:
            raise CollectionStopped("Saved page review IDs are inconsistent")
        if set(page["new_review_ids"]) != set(ids) - seen:
            raise CollectionStopped("Saved page deduplication is inconsistent")
        for review in page["reviews"]:
            validate_review(review)
        digest = hashlib.sha256(raw).hexdigest()
        expected = {"file": path.name, "sha256": digest, "card_count": page["card_count"],
                    "valid_count": page["valid_count"], "new_count": len(page["new_review_ids"]),
                    "collected_at": page["collected_at"], "url": page["url"], "status": page["status"],
                    "errors": []}
        if record and record != expected:
            raise CollectionStopped("Saved page hash or metadata mismatch")
        manifest["pages"][str(number)] = expected  # Recover page saved before manifest commit.
        seen.update(ids)
    if set(manifest.get("unique_review_ids", [])) - seen:
        raise CollectionStopped("Manifest IDs not present in saved pages")
    manifest["unique_review_ids"] = sorted(seen)
    return manifest


def run_collection(config, navigator, *, dry_run=False):
    config.validate()
    if dry_run:
        completed = _load_existing(config)["pages"]
        return {"dry_run": True,
                "pages": [number for number in range(config.start_page, config.end_page + 1)
                          if str(number) not in completed],
                "output_dir": str(config.output_dir), "cdp_connected": False}
    config.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_existing(config)
    atomic_write(config.output_dir / MANIFEST_NAME, json_bytes(manifest))
    seen = set(manifest["unique_review_ids"])
    for number in range(config.start_page, config.end_page + 1):
        if str(number) in manifest["pages"]:
            continue
        try:
            capture = navigator.fetch(number, config.url(number))
            validate_capture(config, number, capture)
            new_reviews = [
                {field: r.get(field) for field in PRIVATE_REVIEW_FIELDS}
                for r in capture["reviews"] if r["source_review_id"] not in seen
            ]
            page = {"company": config.company, "page": number, "url": capture["url"],
                    "collected_at": utc_now(), "status": capture["status"],
                    "card_count": capture["card_count"], "valid_count": len(capture["card_ids"]),
                    "card_ids": capture["card_ids"], "new_review_ids": [r["source_review_id"] for r in new_reviews],
                    "reviews": new_reviews, "errors": []}
            raw = json_bytes(page)
            atomic_write(config.output_dir / page_name(number), raw)
            record = {"file": page_name(number), "sha256": hashlib.sha256(raw).hexdigest(),
                      "card_count": page["card_count"], "valid_count": page["valid_count"],
                      "new_count": len(new_reviews), "collected_at": page["collected_at"],
                      "url": page["url"], "status": page["status"], "errors": []}
            manifest["pages"][str(number)] = record
            seen.update(capture["card_ids"])
            manifest["unique_review_ids"] = sorted(seen)
            manifest["last_error"] = None
            atomic_write(config.output_dir / MANIFEST_NAME, json_bytes(manifest))
        except Exception as exc:
            # Never mark a failed/partially saved page complete. A valid orphan page
            # can be reconciled on --resume without another network request.
            manifest["pages"].pop(str(number), None)
            manifest["last_error"] = {"page": number, "at": utc_now(), "reason": str(exc)}
            try:
                atomic_write(config.output_dir / MANIFEST_NAME, json_bytes(manifest))
            except OSError:
                pass
            raise CollectionStopped(f"Stopped at page {number}: {exc}") from exc
    return manifest


class LiveNavigator:
    def __init__(self, context):
        self.page = context.new_page()
        self.blocked = []
        self.page.on("response", self._on_response)

    def _on_response(self, response):
        host = urlparse(response.url).hostname or ""
        if (host == "trustpilot.com" or host.endswith(".trustpilot.com")) and response.status in (403, 429):
            self.blocked.append(response.status)

    def fetch(self, number, url):
        if self.blocked:
            raise CollectionStopped(f"HTTP {self.blocked[0]}")
        response = self.page.goto(url, wait_until="commit", timeout=30000)
        status = response.status if response else None
        if status in (403, 429) or self.blocked:
            raise CollectionStopped(f"HTTP {status if status in (403, 429) else self.blocked[0]}")
        if status != 200:
            raise CollectionStopped(f"Unexpected HTTP {status}")
        self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        if self.blocked or is_challenge(self.page):
            raise CollectionStopped("HTTP block, CAPTCHA or verification page")
        parsed = urlparse(self.page.url)
        expected = urlparse(url)
        if parsed.hostname != expected.hostname or parsed.path != expected.path or parse_qs(parsed.query) != parse_qs(expected.query):
            raise CollectionStopped("Unexpected final URL or login redirect")
        if response.request.redirected_from is not None:
            raise CollectionStopped("Unexpected redirect")
        self.page.locator(f"{REVIEW_CARD_SELECTOR}:visible").first.wait_for(state="visible", timeout=5000)
        if self.blocked or is_challenge(self.page):
            raise CollectionStopped("HTTP block, CAPTCHA or verification page")
        cards = [card for card in self.page.query_selector_all(REVIEW_CARD_SELECTOR) if card.is_visible()]
        ids = [identity[0] for card in cards if (identity := review_identity_from_card(card))]
        reviews = extract_reviews_from_page(self.page, include_author=False)
        if self.blocked or is_challenge(self.page):
            raise CollectionStopped("HTTP block, CAPTCHA or verification page")
        return {"status": status, "url": self.page.url, "redirected": False,
                "challenge": False, "card_count": len(cards), "card_ids": ids, "reviews": reviews}


def private_default_dir():
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise ValueError("LOCALAPPDATA is required; pass a private --output-dir")
    return Path(root) / "SatisfactionClient" / "TrustpilotSequential"


def ensure_private_dir(path):
    root = Path(os.environ["LOCALAPPDATA"]).resolve() / "SatisfactionClient"
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"Output must be under {root}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", required=True)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=private_default_dir())
    parser.add_argument("--resume", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = Config(args.company, args.start_page, args.end_page, args.output_dir, args.resume)
    config.validate()
    ensure_private_dir(config.output_dir)
    if args.dry_run:
        print(json.dumps(run_collection(config, None, dry_run=True), ensure_ascii=False, indent=2))
        return
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = connect_existing_browser(playwright)
        if len(browser.contexts) != 1:
            raise CollectionStopped("Expected exactly one existing CDP context")
        result = run_collection(config, LiveNavigator(browser.contexts[0]))
        print(json.dumps({"completed_pages": len(result["pages"]),
                          "unique_reviews": len(result["unique_review_ids"]),
                          "manifest": str(config.output_dir / MANIFEST_NAME)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
