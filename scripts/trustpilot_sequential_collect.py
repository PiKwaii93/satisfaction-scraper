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
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from app.scraper import REVIEW_CARD_SELECTOR, extract_reviews_from_page, review_identity_from_card
from scripts.trustpilot_manual_check import connect_existing_browser, is_challenge

MAX_PAGES = 40
MAX_NATURAL_PAGES = 1000
MANIFEST_NAME = "manifest.json"
STACK_SELECTOR = '[data-service-review-stack="true"]'
STACK_BUTTON_SELECTOR = '[data-review-stack-show-button="true"]'
STACK_IDS_JS = """element => [...new Set([...element.querySelectorAll('a[href*="/reviews/"]')]
    .filter(link => link.getClientRects().length)
    .map(link => { try { return new URL(link.href).pathname.match(/^\\/reviews\\/([A-Za-z0-9_-]+)$/)?.[1]; }
                   catch { return null; } })
    .filter(Boolean))]"""
STACK_MAIN_ID_JS = """element => { const link = element.parentElement
    ?.querySelector('article[class*="styles_reviewCard"] a[href*="/reviews/"]');
    try { return new URL(link.href).pathname.match(/^\\/reviews\\/([A-Za-z0-9_-]+)$/)?.[1] || null; }
    catch { return null; } }"""
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
    until_natural_end: bool = False

    def validate(self):
        if not re.fullmatch(r"[A-Za-z0-9.-]+", self.company) or ".." in self.company:
            raise ValueError("Invalid company domain")
        if self.start_page < 1 or self.end_page < self.start_page:
            raise ValueError("Invalid page range")
        limit = MAX_NATURAL_PAGES if self.until_natural_end else MAX_PAGES
        if self.end_page - self.start_page + 1 > limit:
            raise ValueError(f"At most {limit} pages per run")

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


def expand_review_stacks(page, main_ids, check_page):
    """Expand each stack once; fail closed unless every announced ID appears."""
    stacks = page.locator(STACK_SELECTOR)
    count = stacks.count()
    details = []
    observed_extra = set()
    for index in range(count):
        check_page()
        stack = stacks.nth(index)
        raw_count = stack.get_attribute("data-service-review-stack-count")
        if not raw_count or not raw_count.isdecimal() or int(raw_count) < 1:
            raise CollectionStopped(f"Invalid review stack count at stack {index + 1}")
        expected = int(raw_count) - 1
        main_id = stack.evaluate(STACK_MAIN_ID_JS)
        if not main_id or main_id not in main_ids:
            raise CollectionStopped(f"Missing stack main review ID at stack {index + 1}")
        initial = stack.evaluate(STACK_IDS_JS)
        if initial and len(initial) != expected:
            raise CollectionStopped(f"Partially expanded review stack {index + 1}")
        if expected and not initial:
            button = stack.locator(STACK_BUTTON_SELECTOR)
            if button.count() != 1 or not button.is_visible():
                raise CollectionStopped(f"Missing review stack button at stack {index + 1}")
            button.click(timeout=5000)  # Exactly one click; never retry after a failure.
            deadline = time.monotonic() + 8
            while True:
                check_page()
                current = stack.evaluate(STACK_IDS_JS)
                if len(current) >= expected:
                    break
                if time.monotonic() >= deadline:
                    raise CollectionStopped(f"Incomplete review stack {index + 1}: {len(current)}/{expected}")
                page.wait_for_timeout(200)
        else:
            current = initial
        check_page()
        if len(current) != expected or len(set(current)) != expected:
            raise CollectionStopped(f"Incomplete review stack {index + 1}: {len(set(current))}/{expected}")
        if main_id in current or set(current) & (set(main_ids) | observed_extra):
            raise CollectionStopped(f"Duplicate review ID in stack {index + 1}")
        observed_extra.update(current)
        details.append({"main_review_id": main_id, "stack_count": int(raw_count),
                        "expected": expected, "extracted": len(current), "review_ids": current})
    if stacks.count() != count:
        raise CollectionStopped("Review stack inventory changed during expansion")
    return details


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
    validate_stack_structure(capture["main_review_ids"], capture["stack_details"], ids)
    details = capture["stack_details"]
    if len(reviews) != len(ids) or {r.get("source_review_id") for r in reviews} != set(ids):
        raise CollectionStopped("Some visible review cards were not completely parsed")
    for review in reviews:
        validate_review(review)
    if config.until_natural_end:
        next_page = capture.get("next_page")
        if next_page is not None and next_page != number + 1:
            raise CollectionStopped("Unexpected next-page link")
        if next_page is None and (capture.get("next_control_present")
                                  or not capture.get("pagination_present")):
            raise CollectionStopped("Ambiguous natural end: pagination is not conclusive")


def validate_stack_structure(main_ids, details, ids):
    stacked_ids = [review_id for stack in details for review_id in stack["review_ids"]]
    if (not main_ids or len(set(main_ids)) != len(main_ids)
            or len(set(stacked_ids)) != len(stacked_ids)
            or set(main_ids) & set(stacked_ids)
            or set(ids) != set(main_ids) | set(stacked_ids)):
        raise CollectionStopped("Main and stacked review IDs are inconsistent")
    if any(stack["stack_count"] < 1 or stack["expected"] != stack["stack_count"] - 1
           or stack["extracted"] != stack["expected"]
           or len(stack["review_ids"]) != stack["expected"]
           or stack["main_review_id"] not in main_ids for stack in details):
        raise CollectionStopped("Incomplete review stack")


def page_record(page, digest):
    return {"file": page_name(page["page"]), "sha256": digest,
            "card_count": page["card_count"], "valid_count": page["valid_count"],
            "new_count": len(page["new_review_ids"]), "collected_at": page["collected_at"],
            "url": page["url"], "status": page["status"], "errors": [],
            "main_review_count": page["main_review_count"], "stack_count": page["stack_count"],
            "stacked_reviews_expected": page["stacked_reviews_expected"],
            "stacked_reviews_extracted": page["stacked_reviews_extracted"],
            "total_unique_reviews": page["total_unique_reviews"],
            "business_reply_count": page["business_reply_count"],
            "validation_status": page["validation_status"], "next_page": page["next_page"]}


def _load_existing(config):
    manifest_path = config.output_dir / MANIFEST_NAME
    if not config.resume:
        if manifest_path.exists() or any(config.output_dir.glob("page_*.json")):
            raise CollectionStopped("Output already contains a collection; use --resume")
        return {"company": config.company, "start_page": config.start_page,
                "end_page": config.end_page, "created_at": utc_now(), "pages": {},
                "unique_review_ids": [], "last_error": None,
                "until_natural_end": config.until_natural_end, "natural_end_page": None}
    if not manifest_path.exists():
        raise CollectionStopped("No manifest to resume")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("company") != config.company or manifest.get("until_natural_end") != config.until_natural_end:
        raise CollectionStopped("Manifest configuration mismatch")
    saved_start = manifest.get("start_page")
    saved_end = manifest.get("end_page")
    if not isinstance(saved_start, int) or not isinstance(saved_end, int):
        raise CollectionStopped("Invalid manifest page range")
    extending = config.start_page == saved_end + 1 and config.end_page >= config.start_page
    if extending:
        if not config.until_natural_end and config.end_page - saved_start + 1 > MAX_PAGES:
            raise CollectionStopped(f"Combined collection exceeds {MAX_PAGES} pages")
        manifest["end_page"] = config.end_page
    elif not (saved_start <= config.start_page <= config.end_page <= saved_end):
        raise CollectionStopped("Manifest configuration mismatch")
    seen = set()
    for number in range(saved_start, manifest["end_page"] + 1):
        path = config.output_dir / page_name(number)
        record = manifest["pages"].get(str(number))
        if not path.exists():
            if record:
                raise CollectionStopped("Manifest references a missing page file")
            if any(str(later) in manifest["pages"] or (config.output_dir / page_name(later)).exists()
                   for later in range(number + 1, manifest["end_page"] + 1)):
                raise CollectionStopped("Non-contiguous page files")
            break
        raw = path.read_bytes()
        page = json.loads(raw)
        if page.get("page") != number or page.get("company") != config.company:
            raise CollectionStopped("Saved page identity mismatch")
        if page.get("status") != 200 or not page.get("card_ids") or page.get("validation_status") != "completed":
            raise CollectionStopped("Saved page is incomplete")
        ids = page["card_ids"]
        if len(ids) != len(set(ids)) or page.get("valid_count") != len(ids):
            raise CollectionStopped("Saved page counts are inconsistent")
        try:
            validate_stack_structure(page["main_review_ids"], page["stack_details"], ids)
            if (page["main_review_count"] != len(page["main_review_ids"])
                    or page["stack_count"] != len(page["stack_details"])
                    or page["stacked_reviews_expected"] != sum(s["expected"] for s in page["stack_details"])
                    or page["stacked_reviews_extracted"] != sum(s["extracted"] for s in page["stack_details"])
                    or page["total_unique_reviews"] != len(ids)
                    or page["business_reply_count"] > len(ids)):
                raise CollectionStopped("Saved page stack counts are inconsistent")
        except (KeyError, TypeError):
            raise CollectionStopped("Saved page lacks verified review stack metadata") from None
        if set(page.get("new_review_ids", [])) != {r.get("source_review_id") for r in page.get("reviews", [])}:
            raise CollectionStopped("Saved page review IDs are inconsistent")
        if set(page["new_review_ids"]) != set(ids) - seen:
            raise CollectionStopped("Saved page deduplication is inconsistent")
        for review in page["reviews"]:
            validate_review(review)
        digest = hashlib.sha256(raw).hexdigest()
        expected = page_record(page, digest)
        if record and record != expected:
            raise CollectionStopped("Saved page hash or metadata mismatch")
        manifest["pages"][str(number)] = expected  # Recover page saved before manifest commit.
        seen.update(ids)
    if set(manifest.get("unique_review_ids", [])) - seen:
        raise CollectionStopped("Manifest IDs not present in saved pages")
    if extending and any(str(number) not in manifest["pages"] for number in range(saved_start, saved_end + 1)):
        raise CollectionStopped("Cannot extend an incomplete collection")
    first_incomplete = next(
        (number for number in range(saved_start, manifest["end_page"] + 1)
         if str(number) not in manifest["pages"]),
        manifest["end_page"] + 1,
    )
    if config.start_page > first_incomplete:
        raise CollectionStopped("Requested range skips an incomplete page")
    manifest["unique_review_ids"] = sorted(seen)
    if config.until_natural_end:
        observed_ends = [int(number) for number, record in manifest["pages"].items()
                         if record["next_page"] is None]
        if len(observed_ends) > 1:
            raise CollectionStopped("Multiple natural ends in saved pages")
        if observed_ends:
            manifest["natural_end_page"] = observed_ends[0]
    natural_end_page = manifest.get("natural_end_page")
    if natural_end_page is not None and (
            str(natural_end_page) not in manifest["pages"]
            or manifest["pages"][str(natural_end_page)]["next_page"] is not None
            or any(int(number) > natural_end_page for number in manifest["pages"])):
        raise CollectionStopped("Natural end is not backed by a completed page")
    return manifest


def run_collection(config, navigator, *, dry_run=False):
    config.validate()
    if dry_run:
        prior = _load_existing(config)
        completed = prior["pages"]
        return {"dry_run": True,
                "pages": [number for number in range(config.start_page, config.end_page + 1)
                          if str(number) not in completed and
                          (prior.get("natural_end_page") is None or number <= prior["natural_end_page"])],
                "output_dir": str(config.output_dir), "cdp_connected": False}
    config.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_existing(config)
    atomic_write(config.output_dir / MANIFEST_NAME, json_bytes(manifest))
    seen = set(manifest["unique_review_ids"])
    for number in range(config.start_page, config.end_page + 1):
        if manifest.get("natural_end_page") is not None:
            break
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
                    "reviews": new_reviews, "errors": [],
                    "main_review_ids": capture["main_review_ids"],
                    "main_review_count": len(capture["main_review_ids"]),
                    "stack_details": capture["stack_details"],
                    "stack_count": len(capture["stack_details"]),
                    "stacked_reviews_expected": sum(s["expected"] for s in capture["stack_details"]),
                    "stacked_reviews_extracted": sum(s["extracted"] for s in capture["stack_details"]),
                    "total_unique_reviews": len(capture["card_ids"]),
                    "business_reply_count": sum(bool(r["company_responded"]) for r in capture["reviews"]),
                    "validation_status": "completed", "next_page": capture.get("next_page")}
            raw = json_bytes(page)
            atomic_write(config.output_dir / page_name(number), raw)
            record = page_record(page, hashlib.sha256(raw).hexdigest())
            manifest["pages"][str(number)] = record
            if config.until_natural_end and capture.get("next_page") is None:
                manifest["natural_end_page"] = number
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
    if config.until_natural_end and manifest.get("natural_end_page") is None:
        raise CollectionStopped("Safety ceiling reached before a demonstrated natural end; validated pages remain saved")
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

    def _ensure_clean(self, expected_url):
        if self.blocked:
            raise CollectionStopped(f"HTTP {self.blocked[0]}")
        if is_challenge(self.page):
            raise CollectionStopped("CAPTCHA or verification page")
        actual = urlparse(self.page.url)
        expected = urlparse(expected_url)
        if (actual.hostname != expected.hostname or actual.path != expected.path
                or parse_qs(actual.query) != parse_qs(expected.query)):
            raise CollectionStopped("Unexpected final URL or login redirect")

    def _next_page(self, number, expected_url):
        controls = [node for node in self.page.query_selector_all(
            'a[name="pagination-button-next"], a[data-pagination-button-next-link="true"], a[rel="next"]'
        ) if node.is_visible()]
        pagination_present = any(node.is_visible() for node in self.page.query_selector_all(
            '[name^="pagination-button-"], [data-pagination-button-next-link="true"]'
        ))
        hrefs = {node.get_attribute("href") for node in controls if node.get_attribute("href")}
        if len(hrefs) > 1:
            raise CollectionStopped("Conflicting next-page links")
        if not hrefs:
            return None, bool(controls), pagination_present
        next_url = urljoin(expected_url, hrefs.pop())
        parsed = urlparse(next_url)
        expected = urlparse(expected_url)
        next_values = parse_qs(parsed.query).get("page", [])
        if (parsed.hostname != expected.hostname or parsed.path != expected.path
                or len(next_values) != 1 or next_values[0] != str(number + 1)):
            raise CollectionStopped("Unexpected next-page link")
        return number + 1, True, pagination_present

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
        self._ensure_clean(url)
        if response.request.redirected_from is not None:
            raise CollectionStopped("Unexpected redirect")
        self.page.locator(f"{REVIEW_CARD_SELECTOR}:visible").first.wait_for(state="visible", timeout=5000)
        self._ensure_clean(url)
        cards = [card for card in self.page.query_selector_all(REVIEW_CARD_SELECTOR) if card.is_visible()]
        main_ids = [identity[0] for card in cards if (identity := review_identity_from_card(card))]
        stack_details = expand_review_stacks(self.page, main_ids, lambda: self._ensure_clean(url))
        self._ensure_clean(url)
        cards = [card for card in self.page.query_selector_all(REVIEW_CARD_SELECTOR) if card.is_visible()]
        ids = [identity[0] for card in cards if (identity := review_identity_from_card(card))]
        reviews = extract_reviews_from_page(self.page, include_author=False)
        self._ensure_clean(url)
        next_page, next_control_present, pagination_present = self._next_page(number, url)
        return {"status": status, "url": self.page.url, "redirected": False,
                "challenge": False, "card_count": len(cards), "card_ids": ids, "reviews": reviews,
                "main_review_ids": main_ids, "stack_details": stack_details,
                "next_page": next_page, "next_control_present": next_control_present,
                "pagination_present": pagination_present}


def private_default_dir():
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        raise ValueError("LOCALAPPDATA is required; pass a private --output-dir")
    return Path(root) / "SatisfactionClient" / "TrustpilotSequential"


def ensure_private_dir(path):
    # A packaged Windows app can virtualize a newly created LOCALAPPDATA
    # directory into Packages/<app>/LocalCache/Local. Check both the requested
    # lexical path and its real target so resume accepts that private redirect
    # without permitting an output path outside LOCALAPPDATA.
    local = Path(os.path.abspath(os.environ["LOCALAPPDATA"]))
    root = local / "SatisfactionClient"
    requested = Path(os.path.abspath(path))
    if not requested.is_relative_to(root):
        raise ValueError(f"Output must be under {root}")
    relative = requested.relative_to(root)
    actual = requested.resolve()
    virtual_root = local / "Packages"
    virtual_parts = actual.relative_to(virtual_root).parts if actual.is_relative_to(virtual_root) else ()
    expected_tail = ("LocalCache", "Local", "SatisfactionClient", *relative.parts)
    is_packaged_redirect = len(virtual_parts) == len(expected_tail) + 1 and virtual_parts[1:] == expected_tail
    if not actual.is_relative_to(root) and not is_packaged_redirect:
        raise ValueError(f"Output must be under {root}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", required=True)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--until-natural-end", action="store_true",
                        help="Stop only when pagination proves there is no next page; --end-page remains a safety ceiling")
    parser.add_argument("--output-dir", type=Path, default=private_default_dir())
    parser.add_argument("--resume", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = Config(args.company, args.start_page, args.end_page, args.output_dir,
                    args.resume, args.until_natural_end)
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
