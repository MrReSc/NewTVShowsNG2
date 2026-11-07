from __future__ import annotations

import http.client
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urlencode

import pytest

from newtvshowsng2.models import Library, Series
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.server import ApplicationServer
from newtvshowsng2.storage import AnnouncementUnavailable, Storage, _source_key
from test_scanner_and_rendering import Feeds, Jellyfin, release, release_views, setup


class CompletionForms(HTMLParser):
    def __init__(self, html, action="/announcements/complete"):
        super().__init__()
        self.action = action
        self.groups = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("action") == self.action:
            assert attrs.get("method") == "post"
            self.current = []
            self.groups.append(self.current)
        elif tag == "input" and self.current is not None:
            assert attrs.get("name") == "source_key"
            assert attrs.get("type") == "hidden"
            self.current.append(attrs["value"])

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


@pytest.fixture
def app(tmp_path):
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    first = release("The.Walking.Dead.Dead.City.S03E07.German.720p-WAYNE")
    second = replace(
        first, guid="post-2", link="https://feed.test/post-2",
        title="The.Walking.Dead.Dead.City.S03E07.German.1080p-WvF",
    )
    scanner = Scanner(
        cfg, storage, renderer, Jellyfin(Library([series])), Feeds([first, second])
    )
    assert scanner.run_feed()
    return cfg, storage, scanner


def shown_keys(cfg):
    return CompletionForms(cfg.output_path.read_text(encoding="utf-8")).groups[0]


def test_completion_moves_displayed_variants_to_history_without_external_calls(app, monkeypatch):
    cfg, storage, scanner = app
    keys = shown_keys(cfg)
    assert len(keys) == 2
    before = storage.announcements()
    state = storage.state()

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("Erledigen darf weder Jellyfin noch RSS abfragen")

    monkeypatch.setattr(scanner.jellyfin, "load_library", unexpected_call)
    monkeypatch.setattr(scanner.jellyfin, "load_series_episodes", unexpected_call)
    monkeypatch.setattr(scanner.feeds, "load", unexpected_call)
    scanner.complete_announcements(keys)
    rows = storage.announcements()
    assert all(row["completed_at"] is not None for row in rows)
    assert [{**row, "completed_at": None} for row in rows] == before
    assert storage.state() == state
    assert not storage.announcements(current_only=True)
    current, history = release_views(cfg.output_path.read_text(encoding="utf-8"))
    assert "The Walking Dead: Dead City" not in current
    assert 'class="episode-code">S03E07</span>' not in current
    assert history.count('<span class="badge done">Erledigt</span>') == 2
    assert '<span class="badge open">Fehlend</span>' not in history
    assert '<span class="badge new">Neu</span>' not in history
    assert not CompletionForms(history).groups

    scanner.complete_announcements([*keys, keys[0]])
    assert storage.announcements() == rows


def test_completion_survives_restart_and_changed_content_for_same_identity(app):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    completed = {row["source_key"]: row["completed_at"] for row in storage.announcements()}
    updated = [
        replace(item, title=item.title + ".PROPER", content="Neue Beschreibung")
        for item in scanner.feeds.releases
    ]
    reopened = Storage(cfg.database_path)
    reopened.initialize()
    reopened.initialize()
    restarted = Scanner(
        cfg, reopened, Renderer(reopened, cfg.output_path, cfg.timezone),
        scanner.jellyfin, Feeds(updated),
    )
    assert restarted.run_feed()
    assert not reopened.announcements(current_only=True)
    assert {row["source_key"]: row["completed_at"] for row in reopened.announcements()} == completed
    assert all(row["is_new"] for row in reopened.announcements())
    _, history = release_views(cfg.output_path.read_text(encoding="utf-8"))
    assert history.count('class="badge done">Erledigt') == 2
    assert 'class="badge new">Neu' not in history


@pytest.mark.parametrize(
    "marker,guid", [("S03E07", "new-post"), ("S03E08", "new-post"),
                    ("S04E01", "new-post"), ("S03E08", "post-1")],
)
def test_new_feed_identity_is_independent_of_completed_entries(app, marker, guid):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    new = replace(
        scanner.feeds.releases[0], guid=guid,
        title=f"The.Walking.Dead.Dead.City.{marker}.German.2160p-WAYNE",
    )
    scanner.feeds.releases = [*scanner.feeds.releases, new]
    assert scanner.run_feed()
    current = storage.announcements(current_only=True)
    assert len(current) == 1
    assert current[0]["title"] == new.title
    assert current[0]["completed_at"] is None
    assert shown_keys(cfg) == [current[0]["source_key"]]


@pytest.mark.parametrize("guid", ["post-1", None])
@pytest.mark.parametrize("coverage", ["missing", "available", "played"])
def test_republished_season_with_same_link_reopens_only_when_still_missing(
    tmp_path, guid, coverage
):
    cfg, storage, renderer = setup(tmp_path)
    series = Series("decker", "R.J. Decker")
    library = Library([series], missing_episode_tracking_enabled=True)
    library.add_episode(series.id, 2, 1)
    jellyfin = Jellyfin(library, {(series.id, 2): {1, 2}})
    first = replace(
        release(), guid=guid, link="https://feed.test/r-j-decker-s02/",
        title="R.J.Decker.S02.German.DL.1080p.WEB.h264-SAUERKRAUT", content="",
    )
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([first]))
    assert scanner.run_feed()
    old_keys = shown_keys(cfg)
    scanner.complete_announcements(old_keys)
    completed_at = storage.announcements()[0]["completed_at"]

    if coverage == "available":
        jellyfin.library.add_episode(series.id, 2, 2)
    elif coverage == "played":
        jellyfin.played[(series.id, 2)] = {2}
    republished = replace(first, published_at=first.published_at + timedelta(days=7))
    scanner.feeds.releases = [republished]
    assert scanner.run_feed()
    history = storage.announcements()
    assert len(history) == 2
    assert history[1]["source_key"] == old_keys[0]
    assert history[1]["completed_at"] == completed_at
    assert history[0]["completed_at"] is None
    assert history[0]["link"] == history[1]["link"]
    assert history[0]["guid"] == history[1]["guid"]
    current = storage.announcements(current_only=True)
    if coverage == "missing":
        assert [row["source_key"] for row in current] == [history[0]["source_key"]]
        assert shown_keys(cfg) == [history[0]["source_key"]]
        # Ein vor der erneuten Veröffentlichung geöffnetes Formular darf nur
        # seine ursprüngliche Meldung erledigen.
        scanner.complete_announcements(old_keys)
        assert storage.announcements(current_only=True) == current
        scanner.complete_announcements(shown_keys(cfg))
    else:
        assert not current
    assert scanner.run_feed()
    assert len(storage.announcements()) == 2
    assert not storage.announcements(current_only=True)


@pytest.mark.parametrize("original_date_known", [True, False])
@pytest.mark.parametrize("prune", [True, False])
def test_missing_feed_date_does_not_reopen_a_completed_publication(
    app, original_date_known, prune
):
    cfg, storage, scanner = app
    if not original_date_known:
        scanner.feeds.releases = [
            replace(item, guid="undated-" + item.guid, published_at_known=False)
            for item in scanner.feeds.releases
        ]
        assert scanner.run_feed()
    scanner.complete_announcements(shown_keys(cfg))
    before = {row["source_key"]: row["completed_at"] for row in storage.announcements()}
    if prune:
        storage.prune(0)
    scanner.feeds.releases = [
        replace(item, published_at_known=False, published_at=item.published_at + timedelta(days=1))
        for item in scanner.feeds.releases
    ]
    assert scanner.run_feed()
    assert not storage.announcements(current_only=True)
    if not prune:
        assert {row["source_key"]: row["completed_at"] for row in storage.announcements()} == before
    assert scanner.run_feed()
    assert not storage.announcements(current_only=True)


def test_same_publication_in_another_timezone_keeps_its_completion(app):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    before = storage.announcements()
    scanner.feeds.releases = [
        replace(item, published_at=item.published_at.astimezone(timezone(timedelta(hours=1))))
        for item in scanner.feeds.releases
    ]
    assert scanner.run_feed()
    assert not storage.announcements(current_only=True)
    assert [row["source_key"] for row in storage.announcements()] == [
        row["source_key"] for row in before
    ]
    assert [row["completed_at"] for row in storage.announcements()] == [
        row["completed_at"] for row in before
    ]


@pytest.mark.parametrize("reverse", [True, False])
def test_replayed_older_publication_does_not_replace_or_complete_the_new_one(app, reverse):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    first, second = scanner.feeds.releases
    newer = replace(first, published_at=first.published_at + timedelta(days=1))
    publications = [first, newer]
    scanner.feeds.releases = [*(reversed(publications) if reverse else publications), second]
    assert scanner.run_feed()
    assert len(storage.announcements()) == 3
    current = storage.announcements(current_only=True)
    assert len(current) == 1
    assert current[0]["published_at"] == newer.published_at.isoformat()
    assert current[0]["completed_at"] is None


def test_republication_remains_independent_after_restart_and_history_pruning(app):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    first, second = scanner.feeds.releases
    storage.prune(0)
    reopened = Storage(cfg.database_path)
    reopened.initialize()
    newer = replace(first, published_at=first.published_at + timedelta(days=1))
    restarted = Scanner(
        cfg, reopened, Renderer(reopened, cfg.output_path, cfg.timezone),
        scanner.jellyfin, Feeds([first, newer, second]),
    )
    assert restarted.run_feed()
    current = reopened.announcements(current_only=True)
    assert len(current) == 1
    assert current[0]["published_at"] == newer.published_at.isoformat()
    assert current[0]["completed_at"] is None


def use_legacy_keys(storage):
    rows = storage.announcements()
    with sqlite3.connect(storage.path) as connection:
        for row in rows:
            old_key = _source_key(row["feed_item_key"], row["season"], row["episode"])
            connection.execute(
                "UPDATE announcements SET source_key = ? WHERE source_key = ?",
                (old_key, row["source_key"]),
            )
            connection.execute(
                "UPDATE announcement_completions SET source_key = ? WHERE source_key = ?",
                (old_key, row["source_key"]),
            )
        connection.execute(
            "DELETE FROM announcement_completions WHERE source_key NOT IN "
            "(SELECT source_key FROM announcements)"
        )


@pytest.mark.parametrize("republish", [False, True])
def test_legacy_completions_keep_their_original_publication(app, republish):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    completed = {row["guid"]: row["completed_at"] for row in storage.announcements()}
    use_legacy_keys(storage)
    if republish:
        first, second = scanner.feeds.releases
        scanner.feeds.releases = [
            replace(first, published_at=first.published_at + timedelta(days=1)), second,
        ]
    assert scanner.run_feed()
    assert len(storage.announcements()) == 2 + int(republish)
    assert len(storage.announcements(current_only=True)) == int(republish)
    assert {
        row["guid"]: row["completed_at"]
        for row in storage.announcements() if row["completed_at"] is not None
    } == completed
    assert scanner.run_feed()
    assert len(storage.announcements()) == 2 + int(republish)


def test_pruned_legacy_completion_does_not_hide_later_publications(app):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    completed_at = datetime.fromisoformat(storage.announcements()[0]["completed_at"])
    use_legacy_keys(storage)
    storage.prune(0)
    assert scanner.run_feed()
    assert not storage.announcements(current_only=True)
    first, second = scanner.feeds.releases
    scanner.feeds.releases = [
        replace(first, published_at=completed_at + timedelta(days=1)), second,
    ]
    assert scanner.run_feed()
    current = storage.announcements(current_only=True)
    assert len(current) == 1
    assert current[0]["guid"] == first.guid


def test_conflicting_publication_migration_rolls_back_completions(app):
    cfg, storage, scanner = app
    scanner.complete_announcements(shown_keys(cfg))
    use_legacy_keys(storage)
    with sqlite3.connect(storage.path) as connection:
        connection.row_factory = sqlite3.Row
        row = dict(connection.execute("SELECT * FROM announcements LIMIT 1").fetchone())
        row["source_key"] = _source_key(
            row["feed_item_key"], row["season"], row["episode"],
            datetime.fromisoformat(row["published_at"]),
        )
        connection.execute(
            f"INSERT INTO announcements ({', '.join(row)}) "
            f"VALUES ({', '.join('?' for _ in row)})",
            tuple(row.values()),
        )
        before = connection.execute(
            "SELECT * FROM announcement_completions ORDER BY source_key"
        ).fetchall()
    history = storage.announcements()
    assert not scanner.run_feed()
    assert storage.state()["scan_status"] == "error"
    after = storage.announcements()
    assert [{**row, "is_new": 0} for row in after] == [
        {**row, "is_new": 0} for row in history
    ]
    with sqlite3.connect(storage.path) as connection:
        assert connection.execute(
            "SELECT * FROM announcement_completions ORDER BY source_key"
        ).fetchall() == [tuple(row) for row in before]


def test_history_pruning_preserves_completions_when_feed_entries_return(app):
    cfg, storage, scanner = app
    keys = shown_keys(cfg)
    scanner.complete_announcements(keys)
    completed = {row["source_key"]: row["completed_at"] for row in storage.announcements()}
    original = list(scanner.feeds.releases)
    new = replace(
        original[0], guid="new-post",
        title="The.Walking.Dead.Dead.City.S03E08.German",
        published_at=original[0].published_at - timedelta(days=1),
    )
    scanner.feeds.releases = [*original, new]
    scanner.config = replace(cfg, max_history=1)
    assert scanner.run_feed()
    assert [row["title"] for row in storage.announcements()] == [new.title]
    storage.complete_announcements(keys, datetime.now(UTC) + timedelta(days=1))

    scanner.config = cfg
    storage.initialize()
    assert scanner.run_feed()
    assert len(storage.announcements()) == 3
    assert [row["title"] for row in storage.announcements(current_only=True)] == [new.title]
    assert {
        row["source_key"]: row["completed_at"]
        for row in storage.announcements() if row["source_key"] in keys
    } == completed


def test_unknown_key_does_not_partially_complete_other_entries(app):
    cfg, storage, scanner = app
    keys = shown_keys(cfg)
    with pytest.raises(AnnouncementUnavailable):
        scanner.complete_announcements([keys[0], "f" * 64])
    assert all(row["completed_at"] is None for row in storage.announcements())
    scanner.complete_announcements([keys[0]])
    assert [row["source_key"] for row in storage.announcements(current_only=True)] == [keys[1]]


def test_completion_waits_for_feed_run_and_leaves_new_variants_open(app):
    cfg, storage, scanner = app
    keys = shown_keys(cfg)
    entered = threading.Event()
    release_scan = threading.Event()
    attempting_completion = threading.Event()
    completed = threading.Event()
    new = replace(scanner.feeds.releases[0], guid="post-3", link="https://feed.test/post-3")

    class BlockingFeeds(Feeds):
        def load(self, url):
            entered.set()
            assert release_scan.wait(timeout=5)
            return super().load(url)

    scanner.feeds = BlockingFeeds([*scanner.feeds.releases, new])

    def complete():
        attempting_completion.set()
        scanner.complete_announcements(keys)
        completed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        scan = pool.submit(scanner.run_feed)
        try:
            assert entered.wait(timeout=3)
            completion = pool.submit(complete)
            assert attempting_completion.wait(timeout=3)
            assert not completed.wait(timeout=0.05)
            release_scan.set()
            assert scan.result(timeout=3)
            completion.result(timeout=3)
        finally:
            release_scan.set()
    current = storage.announcements(current_only=True)
    assert len(current) == 1
    assert current[0]["guid"] == "post-3"
    assert shown_keys(cfg) == [current[0]["source_key"]]


@pytest.fixture
def http_app(app, tmp_path):
    cfg, storage, scanner = app
    server = ApplicationServer(
        ("127.0.0.1", 0), cfg.output_path, storage, tmp_path / "app.log",
        cfg.timezone, scanner,
    )
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"

    def request(body, headers=None, method="POST", path="/announcements/complete"):
        request_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        request_headers.update({"Origin": origin} if headers is None else headers)
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        try:
            connection.request(method, path, body, request_headers)
            response = connection.getresponse()
            return response.status, response.getheader("Location"), response.read().decode("utf-8")
        finally:
            connection.close()

    try:
        yield request, origin
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_completion_endpoint_redirects_and_accepts_repeated_clicks(app, http_app):
    cfg, storage, _ = app
    request, _ = http_app
    body = urlencode({"source_key": shown_keys(cfg)}, doseq=True)
    assert request(body)[:2] == (303, "/#overview")
    rows = storage.announcements()
    assert all(row["completed_at"] for row in rows)
    assert request(body)[:2] == (303, "/#overview")
    assert storage.announcements() == rows
    assert request("", method="GET")[0] == 404


def test_completion_endpoint_rejects_foreign_origins_and_malformed_forms(app, http_app):
    cfg, storage, _ = app
    request, origin = http_app
    keys = shown_keys(cfg)
    body = urlencode({"source_key": keys}, doseq=True)
    for headers in (
        {}, {"Origin": "http://foreign.test"}, {"Referer": "http://foreign.test/page"},
        {"Origin": origin, "Sec-Fetch-Site": "cross-site"},
    ):
        assert request(body, headers)[0] == 403
    for invalid_body in (
        "", "source_key=", "source_key=bad", b"\xff", "source_key",
        f"other={keys[0]}", f"source_key={keys[0]}&other=x", "x" * 65537,
    ):
        assert request(invalid_body)[0] == 400
    assert request(body, {"Origin": origin, "Content-Type": "application/json"})[0] == 400
    assert request(urlencode({"source_key": [keys[0], "f" * 64]}, doseq=True))[0] == 409
    assert all(row["completed_at"] is None for row in storage.announcements())
    assert request(body, {"Referer": origin + "/"})[0] == 303


def test_completion_can_be_retried_after_render_failure(app, http_app, monkeypatch):
    cfg, storage, scanner = app
    request, _ = http_app
    body = urlencode({"source_key": shown_keys(cfg)}, doseq=True)
    render = scanner.renderer.render

    def fail_render():
        raise OSError("Ausgabe nicht verfügbar")

    monkeypatch.setattr(scanner.renderer, "render", fail_render)
    assert request(body)[0] == 500
    assert not storage.announcements(current_only=True)
    monkeypatch.setattr(scanner.renderer, "render", render)
    assert request(body)[:2] == (303, "/#overview")
    current, history = release_views(cfg.output_path.read_text(encoding="utf-8"))
    assert "The Walking Dead: Dead City" not in current
    assert 'class="episode-code">S03E07</span>' not in current
    assert history.count('class="badge done">Erledigt') == 2
