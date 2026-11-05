import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from urllib.parse import urlencode

import pytest

from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.models import Library, SeasonInventory, Series
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.storage import AnnouncementUnavailable, Storage
from test_announcement_completions import CompletionForms, app, http_app, shown_keys, use_legacy_keys
from test_scanner_and_rendering import Feeds, Jellyfin, release_views


def complete(app):
    cfg, storage, scanner = app
    keys = shown_keys(cfg)
    scanner.complete_announcements(keys)
    return keys


def completions(storage):
    with sqlite3.connect(storage.path) as connection:
        return connection.execute(
            "SELECT * FROM announcement_completions ORDER BY source_key"
        ).fetchall()


def test_history_can_reopen_one_variant_without_rss_or_media_actions(app, monkeypatch):
    cfg, storage, scanner = app
    keys = complete(app)
    state = storage.state()
    forms = CompletionForms(cfg.output_path.read_text(), "/announcements/reopen").groups
    assert sorted(forms) == sorted([[key] for key in keys])

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("Wiederöffnen darf weder RSS noch Medienimport ausführen")

    monkeypatch.setattr(scanner.feeds, "load", unexpected_call)
    monkeypatch.setattr(scanner, "_import_media", unexpected_call)
    scanner.reopen_announcements([keys[0]])
    rows = {row["source_key"]: row for row in storage.announcements()}
    assert rows[keys[0]]["completed_at"] is None
    assert rows[keys[1]]["completed_at"] is not None
    assert [row["source_key"] for row in storage.announcements(current_only=True)] == [keys[0]]
    assert storage.state() == state
    current, history = release_views(cfg.output_path.read_text())
    assert "Dead City · S03E07" in current
    assert CompletionForms(history, "/announcements/reopen").groups == [[keys[1]]]
    assert history.count('class="badge done">Erledigt') == 1
    assert history.count('class="badge open">Fehlend') == 1
    assert 'class="badge new">Neu' not in current


@pytest.mark.parametrize("coverage", ["missing", "available", "played"])
def test_reopening_uses_fresh_jellyfin_identity_and_episode_status(app, coverage):
    cfg, storage, scanner = app
    keys = complete(app)
    series = Series("new-id", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    if coverage == "available":
        library.add_episode(series.id, 3, 7)
    played = {(series.id, 3): {7}} if coverage == "played" else {}
    scanner.jellyfin = Jellyfin(library, {(series.id, 3): {7}}, played=played)
    scanner.reopen_announcements([keys[0]])
    rows = {row["source_key"]: row for row in storage.announcements()}
    assert rows[keys[0]]["matched_series_id"] == "new-id"
    assert rows[keys[0]]["status_reason"] == coverage
    assert rows[keys[0]]["completed_at"] is None
    assert rows[keys[1]]["matched_series_id"] == "dead-city"
    assert rows[keys[1]]["completed_at"] is not None
    assert bool(storage.announcements(current_only=True)) == (coverage == "missing")
    assert scanner.jellyfin.series_calls == [series.id]


@pytest.mark.parametrize("coverage", ["missing", "available", "played", "covered", "unknown"])
def test_reopening_season_release_uses_current_available_and_played_episodes(app, coverage):
    cfg, storage, scanner = app
    scanner.feeds.releases = [
        replace(item, title=item.title.replace("S03E07", "S03"))
        for item in scanner.feeds.releases
    ]
    assert scanner.run_feed()
    keys = complete(app)
    series = scanner.jellyfin.library.series[0]
    library = Library([series], missing_episode_tracking_enabled=coverage != "unknown")
    available = {1, 2, 3} if coverage == "available" else {1}
    if coverage == "played":
        available = set()
    for episode in available:
        library.add_episode(series.id, 3, episode)
    played = {1, 2, 3} if coverage == "played" else {2, 3} if coverage == "covered" else {2}
    scanner.jellyfin = Jellyfin(
        library, {(series.id, 3): {1, 2, 3}}, played={(series.id, 3): played}
    )
    scanner.reopen_announcements([keys[0]])
    row = next(row for row in storage.announcements() if row["source_key"] == keys[0])
    assert row["status_reason"] == ("missing" if coverage == "unknown" else coverage)
    assert bool(storage.announcements(current_only=True)) == (coverage in {"missing", "unknown"})
    assert row["needed_episodes"] == ({"missing": [3], "unknown": None}.get(coverage, []))


def test_invalid_feed_metadata_blocks_the_whole_reopening_request(app):
    cfg, storage, scanner = app
    keys = complete(app)
    with sqlite3.connect(storage.path) as connection:
        connection.execute(
            "UPDATE announcements SET title = ? WHERE source_key = ?",
            ("Kein gültiger Feed-Titel", keys[1]),
        )
    before = storage.announcements()
    before_completions = completions(storage)
    with pytest.raises(AnnouncementUnavailable):
        scanner.reopen_announcements(keys)
    assert storage.announcements() == before
    assert completions(storage) == before_completions


def test_reopening_and_completing_again_are_idempotent(app):
    cfg, storage, scanner = app
    keys = complete(app)
    scanner.reopen_announcements([keys[0], keys[0]])
    before = completions(storage)
    scanner.reopen_announcements([keys[0]])
    assert completions(storage) == before
    scanner.complete_announcements([keys[0]])
    assert not storage.announcements(current_only=True)
    before = completions(storage)
    scanner.complete_announcements([keys[0]])
    assert completions(storage) == before
    assert CompletionForms(cfg.output_path.read_text(), "/announcements/reopen").groups
    storage.prune(0)
    scanner.feeds.releases = [
        replace(item, published_at_known=False) for item in scanner.feeds.releases
    ]
    assert scanner.run_feed()
    assert not storage.announcements(current_only=True)


@pytest.mark.parametrize("date_mode", ["dated", "undated", "date_disappears"])
def test_reopened_publication_survives_restart_pruning_and_fallback_markers(app, date_mode):
    cfg, storage, scanner = app
    if date_mode != "dated":
        scanner.feeds.releases = [
            replace(
                item, published_at_known=False,
                guid="undated-" + item.guid if date_mode == "undated" else item.guid,
            ) for item in scanner.feeds.releases
        ]
        assert scanner.run_feed()
    keys = complete(app)
    first, second = scanner.feeds.releases
    target = next(row["source_key"] for row in storage.announcements() if row["guid"] == first.guid)
    if date_mode == "dated":
        newer = replace(first, published_at=first.published_at + timedelta(days=1))
        scanner.feeds.releases = [first, newer, second]
        assert scanner.run_feed()
        scanner.complete_announcements(shown_keys(cfg))
    scanner.reopen_announcements([target])
    storage.prune(0)
    reopened = Storage(cfg.database_path)
    reopened.initialize()
    restarted = Scanner(
        cfg, reopened, Renderer(reopened, cfg.output_path, cfg.timezone),
        scanner.jellyfin, scanner.feeds,
    )
    assert restarted.run_feed()
    current = reopened.announcements(current_only=True)
    assert len(current) == 1
    if date_mode != "date_disappears":
        assert current[0]["source_key"] == target
    assert current[0]["guid"] == first.guid
    assert all(
        row["completed_at"] is not None for row in reopened.announcements()
        if row["source_key"] != current[0]["source_key"]
    )


def test_migrating_legacy_keys_preserves_reopening(app):
    cfg, storage, scanner = app
    keys = complete(app)
    scanner.reopen_announcements([keys[0]])
    use_legacy_keys(storage)
    assert scanner.run_feed()
    assert [row["source_key"] for row in storage.announcements(current_only=True)] == [keys[0]]


@pytest.mark.parametrize("failure", ["library", "episodes", "played", "inconsistent"])
def test_failed_fresh_jellyfin_check_keeps_completions_and_history(app, monkeypatch, failure):
    cfg, storage, scanner = app
    keys = complete(app)
    before = storage.announcements()
    before_completions = completions(storage)
    if failure == "library":
        def unavailable():
            raise JellyfinError("Jellyfin ist nicht erreichbar")
        monkeypatch.setattr(scanner.jellyfin, "load_library", unavailable)
    elif failure == "episodes":
        scanner.jellyfin.error = JellyfinError("Episoden konnten nicht gelesen werden")
    elif failure == "played":
        monkeypatch.setattr(
            scanner.jellyfin, "load_series_episodes",
            lambda _sid: {3: SeasonInventory({7}, played_status_complete=False)},
        )
    else:
        scanner.jellyfin.library.add_episode("dead-city", 3, 7)
    with pytest.raises(JellyfinError):
        scanner.reopen_announcements(keys)
    assert storage.announcements() == before
    assert completions(storage) == before_completions


@pytest.mark.parametrize("ambiguous", [False, True])
def test_missing_or_ambiguous_current_series_blocks_reopening(app, ambiguous):
    cfg, storage, scanner = app
    keys = complete(app)
    before = storage.announcements()
    before_completions = completions(storage)
    scanner.jellyfin.library.series = [
        Series(str(index), "The Walking Dead: Dead City", imdb_id="tt18546730")
        for index in range(2)
    ] if ambiguous else []
    with pytest.raises(AnnouncementUnavailable, match="nicht eindeutig"):
        scanner.reopen_announcements([keys[0]])
    assert storage.announcements() == before
    assert completions(storage) == before_completions


def test_invalid_or_pruned_keys_do_not_partially_reopen_entries(app):
    cfg, storage, scanner = app
    keys = complete(app)
    before = completions(storage)
    with pytest.raises(AnnouncementUnavailable):
        scanner.reopen_announcements([keys[0], "f" * 64])
    assert completions(storage) == before
    storage.prune(0)
    with pytest.raises(AnnouncementUnavailable):
        scanner.reopen_announcements([keys[0]])
    assert completions(storage) == before


def test_reopening_waits_for_running_feed_and_leaves_new_publication_untouched(app):
    cfg, storage, scanner = app
    keys = complete(app)
    first, second = scanner.feeds.releases
    newer = replace(first, published_at=first.published_at + timedelta(days=1))
    entered = threading.Event()
    release_feed = threading.Event()
    attempting_reopen = threading.Event()
    reopened = threading.Event()

    class BlockingFeeds(Feeds):
        def load(self, url):
            entered.set()
            assert release_feed.wait(timeout=5)
            return super().load(url)

    scanner.feeds = BlockingFeeds([first, newer, second])

    def reopen():
        attempting_reopen.set()
        scanner.reopen_announcements([keys[0]])
        reopened.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        feed = pool.submit(scanner.run_feed)
        try:
            assert entered.wait(timeout=3)
            undo = pool.submit(reopen)
            assert attempting_reopen.wait(timeout=3)
            assert not reopened.wait(timeout=0.05)
            release_feed.set()
            assert feed.result(timeout=3)
            undo.result(timeout=3)
        finally:
            release_feed.set()
    current = storage.announcements(current_only=True)
    assert len(current) == 2
    assert keys[0] in {row["source_key"] for row in current}
    assert any(row["published_at"] == newer.published_at.isoformat() for row in current)


def test_reopen_endpoint_redirects_and_accepts_repeated_requests(app, http_app):
    cfg, storage, scanner = app
    keys = complete(app)
    request, _ = http_app
    body = urlencode({"source_key": keys[0]})
    assert request(body, path="/announcements/reopen")[:2] == (303, "/#history")
    before = completions(storage)
    assert request(body, path="/announcements/reopen")[:2] == (303, "/#history")
    assert completions(storage) == before
    assert [row["source_key"] for row in storage.announcements(current_only=True)] == [keys[0]]
    assert request("", method="GET", path="/announcements/reopen")[0] == 404


def test_reopen_endpoint_rejects_foreign_origins_and_invalid_forms(app, http_app):
    cfg, storage, scanner = app
    keys = complete(app)
    request, origin = http_app
    body = urlencode({"source_key": keys[0]})
    before = completions(storage)
    for headers in (
        {}, {"Origin": "http://foreign.test"}, {"Referer": "http://foreign.test/page"},
        {"Origin": origin, "Sec-Fetch-Site": "cross-site"},
    ):
        assert request(body, headers, path="/announcements/reopen")[0] == 403
    for invalid in ("", "source_key=bad", b"\xff", "source_key", f"other={keys[0]}"):
        assert request(invalid, path="/announcements/reopen")[0] == 400
    assert request(
        body, {"Origin": origin, "Content-Type": "application/json"}, path="/announcements/reopen"
    )[0] == 400
    assert request(
        urlencode({"source_key": [keys[0], "f" * 64]}, doseq=True), path="/announcements/reopen"
    )[0] == 409
    assert completions(storage) == before


def test_reopen_endpoint_reports_jellyfin_failure_without_changing_completion(app, http_app):
    cfg, storage, scanner = app
    keys = complete(app)
    request, _ = http_app
    before = completions(storage)
    scanner.jellyfin.error = JellyfinError("Jellyfin ist nicht erreichbar")
    assert request(
        urlencode({"source_key": keys[0]}), path="/announcements/reopen"
    )[0] == 503
    assert completions(storage) == before


def test_reopen_endpoint_can_retry_after_render_failure(app, http_app, monkeypatch):
    cfg, storage, scanner = app
    keys = complete(app)
    request, _ = http_app
    body = urlencode({"source_key": keys[0]})
    render = scanner.renderer.render

    def unavailable():
        raise OSError("Ausgabe ist nicht verfügbar")

    monkeypatch.setattr(scanner.renderer, "render", unavailable)
    assert request(body, path="/announcements/reopen")[0] == 500
    assert [row["source_key"] for row in storage.announcements(current_only=True)] == [keys[0]]
    before = completions(storage)
    monkeypatch.setattr(scanner.renderer, "render", render)
    assert request(body, path="/announcements/reopen")[:2] == (303, "/#history")
    assert completions(storage) == before
