"""Offline-only tests: no CDP browser or Trustpilot request."""

import json
from pathlib import Path

import pytest

from scripts import trustpilot_sequential_collect as collector


def review(review_id, *, reply=False):
    return {
        "source_review_id": review_id,
        "review_url": f"https://fr.trustpilot.com/reviews/{review_id}",
        "rating": 4,
        "date": "2026-09-25",
        "title": "Titre anonymisé",
        "verbatim": "Commentaire anonymisé",
        "company_responded": reply,
        "company_reply_text": "Réponse anonymisée" if reply else None,
        "company_reply_date": "2026-09-25" if reply else None,
    }


class FakeNavigator:
    def __init__(self, captures):
        self.captures = captures
        self.calls = []

    def fetch(self, number, url):
        self.calls.append(number)
        return self.captures[number]


def config(tmp_path, end=2, resume=False):
    return collector.Config("example.com", 1, end, tmp_path / "private", resume)


def capture(cfg, number, reviews, *, status=200, card_count=None, **changes):
    value = {"status": status, "url": cfg.url(number), "redirected": False,
             "challenge": False, "card_count": len(reviews) if card_count is None else card_count,
             "card_ids": [r["source_review_id"] for r in reviews], "reviews": reviews}
    value.update(changes)
    return value


def manifest(cfg):
    return json.loads((cfg.output_dir / "manifest.json").read_text(encoding="utf-8"))


def test_valid_page_and_annex_cards(tmp_path):
    cfg = config(tmp_path, end=1)
    nav = FakeNavigator({1: capture(cfg, 1, [review("a", reply=True)], card_count=2)})
    result = collector.run_collection(cfg, nav)
    assert nav.calls == [1]
    assert result["unique_review_ids"] == ["a"]
    assert result["pages"]["1"]["card_count"] == 2
    assert result["pages"]["1"]["valid_count"] == 1


def test_cross_page_duplicate_by_stable_id(tmp_path):
    cfg = config(tmp_path)
    nav = FakeNavigator({1: capture(cfg, 1, [review("a")]),
                         2: capture(cfg, 2, [review("a"), review("b")])})
    result = collector.run_collection(cfg, nav)
    saved = json.loads((cfg.output_dir / "page_0002.json").read_text(encoding="utf-8"))
    assert result["unique_review_ids"] == ["a", "b"]
    assert saved["new_review_ids"] == ["b"]
    assert saved["valid_count"] == 2


def test_unneeded_author_field_is_not_saved(tmp_path):
    cfg = config(tmp_path, end=1)
    source = {**review("a"), "author": "Name that must not be stored"}
    collector.run_collection(cfg, FakeNavigator({1: capture(cfg, 1, [source])}))
    saved = (cfg.output_dir / "page_0001.json").read_text(encoding="utf-8")
    assert "author" not in saved
    assert "Name that must not be stored" not in saved


@pytest.mark.parametrize("reviews,reason", [([], "Empty page"),
    ([{**review("a"), "date": None}], "review date"),
    ([{**review("a"), "company_reply_date": None, "company_responded": True,
       "company_reply_text": "Réponse anonymisée"}], "reply date")])
def test_invalid_page_never_marked_complete(tmp_path, reviews, reason):
    cfg = config(tmp_path)
    nav = FakeNavigator({1: capture(cfg, 1, reviews)})
    with pytest.raises(collector.CollectionStopped, match=reason):
        collector.run_collection(cfg, nav)
    assert nav.calls == [1]
    assert manifest(cfg)["pages"] == {}
    assert not (cfg.output_dir / "page_0001.json").exists()


@pytest.mark.parametrize("status", [403, 429])
def test_http_block_stops_without_retry(tmp_path, status):
    cfg = config(tmp_path)
    nav = FakeNavigator({1: capture(cfg, 1, [], status=status)})
    with pytest.raises(collector.CollectionStopped, match=str(status)):
        collector.run_collection(cfg, nav)
    assert nav.calls == [1]
    assert manifest(cfg)["pages"] == {}


def test_parser_gap_stops_page(tmp_path):
    cfg = config(tmp_path)
    bad = capture(cfg, 1, [review("a")], card_count=2, card_ids=["a", "b"])
    with pytest.raises(collector.CollectionStopped, match="not completely parsed"):
        collector.run_collection(cfg, FakeNavigator({1: bad}))
    assert manifest(cfg)["pages"] == {}


@pytest.mark.parametrize("changes,reason", [
    ({"challenge": True}, "CAPTCHA"),
    ({"redirected": True}, "Redirect"),
    ({"url": "https://fr.trustpilot.com/users/connect"}, "final URL"),
])
def test_challenge_and_redirect_stop(tmp_path, changes, reason):
    cfg = config(tmp_path)
    nav = FakeNavigator({1: capture(cfg, 1, [review("a")], **changes)})
    with pytest.raises(collector.CollectionStopped, match=reason):
        collector.run_collection(cfg, nav)
    assert nav.calls == [1]
    assert manifest(cfg)["pages"] == {}


def test_resume_skips_valid_completed_page(tmp_path):
    cfg = config(tmp_path)
    first = FakeNavigator({1: capture(cfg, 1, [review("a")]), 2: capture(cfg, 2, [], status=403)})
    with pytest.raises(collector.CollectionStopped):
        collector.run_collection(cfg, first)
    second = FakeNavigator({2: capture(cfg, 2, [review("a"), review("b")])})
    result = collector.run_collection(config(tmp_path, resume=True), second)
    assert second.calls == [2]
    assert result["unique_review_ids"] == ["a", "b"]


def test_manifest_write_interruption_recovers_saved_page(tmp_path, monkeypatch):
    cfg = config(tmp_path, end=1)
    original = collector.atomic_write
    calls = 0

    def fail_manifest_once(path, content):
        nonlocal calls
        if Path(path).name == "manifest.json":
            calls += 1
            if calls == 2:
                raise OSError("simulated interruption")
        return original(path, content)

    monkeypatch.setattr(collector, "atomic_write", fail_manifest_once)
    with pytest.raises(collector.CollectionStopped):
        collector.run_collection(cfg, FakeNavigator({1: capture(cfg, 1, [review("a")])}))
    monkeypatch.setattr(collector, "atomic_write", original)
    nav = FakeNavigator({})
    result = collector.run_collection(config(tmp_path, end=1, resume=True), nav)
    assert nav.calls == []
    assert result["pages"]["1"]["new_count"] == 1


def test_maximum_pages_and_dry_run_never_connects(tmp_path):
    cfg = collector.Config("example.com", 11, 50, tmp_path / "private")
    plan = collector.run_collection(cfg, None, dry_run=True)
    assert len(plan["pages"]) == 40
    assert plan["cdp_connected"] is False
    assert not cfg.output_dir.exists()
    with pytest.raises(ValueError, match="At most 40"):
        collector.run_collection(collector.Config("example.com", 11, 51, tmp_path / "private"),
                                 None, dry_run=True)


def test_dry_run_resume_shows_only_remaining_pages(tmp_path):
    cfg = config(tmp_path)
    first = FakeNavigator({1: capture(cfg, 1, [review("a")]), 2: capture(cfg, 2, [], status=429)})
    with pytest.raises(collector.CollectionStopped):
        collector.run_collection(cfg, first)
    before = (cfg.output_dir / "manifest.json").read_bytes()
    plan = collector.run_collection(config(tmp_path, resume=True), None, dry_run=True)
    assert plan["pages"] == [2]
    assert (cfg.output_dir / "manifest.json").read_bytes() == before


def test_contiguous_extension_preserves_prior_pages_and_full_resume_skips_all(tmp_path):
    initial = config(tmp_path)
    collector.run_collection(initial, FakeNavigator({
        1: capture(initial, 1, [review("a")]),
        2: capture(initial, 2, [review("b")]),
    }))
    extended = collector.Config("example.com", 3, 4, initial.output_dir, True)
    navigator = FakeNavigator({
        3: capture(extended, 3, [review("b"), review("c")]),
        4: capture(extended, 4, [review("d")]),
    })
    result = collector.run_collection(extended, navigator)
    assert navigator.calls == [3, 4]
    assert result["start_page"] == 1 and result["end_page"] == 4
    assert result["unique_review_ids"] == ["a", "b", "c", "d"]
    assert result["pages"]["3"]["new_count"] == 1
    full = collector.Config("example.com", 1, 4, initial.output_dir, True)
    no_fetch = FakeNavigator({})
    collector.run_collection(full, no_fetch)
    assert no_fetch.calls == []


def test_extension_rejects_incomplete_prior_range(tmp_path):
    initial = config(tmp_path)
    with pytest.raises(collector.CollectionStopped):
        collector.run_collection(initial, FakeNavigator({
            1: capture(initial, 1, [review("a")]),
            2: capture(initial, 2, [], status=403),
        }))
    extension = collector.Config("example.com", 3, 4, initial.output_dir, True)
    no_fetch = FakeNavigator({})
    with pytest.raises(collector.CollectionStopped, match="incomplete"):
        collector.run_collection(extension, no_fetch)
    assert no_fetch.calls == []


def test_extension_rejects_more_than_40_combined_pages(tmp_path):
    initial = collector.Config("example.com", 11, 13, tmp_path / "private")
    collector.run_collection(initial, FakeNavigator({
        number: capture(initial, number, [review(str(number))]) for number in range(11, 14)
    }))
    extension = collector.Config("example.com", 14, 51, initial.output_dir, True)
    with pytest.raises(collector.CollectionStopped, match="exceeds 40"):
        collector.run_collection(extension, FakeNavigator({}), dry_run=True)


def test_private_path_accepts_packaged_app_virtualization(tmp_path, monkeypatch):
    local = tmp_path / "Local"
    requested = local / "SatisfactionClient" / "TrustpilotSequential"
    redirected = (
        local / "Packages" / "CodexApp" / "LocalCache" / "Local"
        / "SatisfactionClient" / "TrustpilotSequential"
    )
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setattr(Path, "resolve", lambda self: redirected)
    collector.ensure_private_dir(requested)
    with pytest.raises(ValueError, match="Output must be under"):
        collector.ensure_private_dir(tmp_path / "public-repository")
    monkeypatch.setattr(Path, "resolve", lambda self: local / "Other" / "SatisfactionClient" / "TrustpilotSequential")
    with pytest.raises(ValueError, match="Output must be under"):
        collector.ensure_private_dir(requested)
