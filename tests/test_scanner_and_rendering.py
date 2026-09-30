from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from newtvshowsng2.config import Config
from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.models import FeedRelease, Library, SeasonInventory, Series
from newtvshowsng2.rendering import Renderer, group_current_releases
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.storage import Storage


class Jellyfin:
    def __init__(self, library, expected=None, error=None, played=None):
        self.library = library
        self.expected = expected or {}
        self.error = error
        self.played = played or {}
        self.series_calls = []

    def load_library(self):
        return deepcopy(self.library)

    def load_series_episodes(self, series_id):
        self.series_calls.append(series_id)
        if self.error:
            raise self.error
        return {
            season: SeasonInventory(
                set(episodes), set(self.played.get((sid, season), set()))
            )
            for (sid, season), episodes in self.expected.items()
            if sid == series_id
        }


class Feeds:
    def __init__(self, releases):
        self.releases = releases

    def load(self, _url):
        return self.releases


def config(tmp_path: Path) -> Config:
    return Config(
        jellyfin_url="http://jellyfin.test",
        jellyfin_api_key="secret",
        jellyfin_username="Hans",
        rss_urls=("https://feed.test/rss",),
        check_interval_hours=1,
        max_history=300,
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "out",
    )


def release(title="The.Walking.Dead.Dead.City.S03.German") -> FeedRelease:
    return FeedRelease(
        feed_url="https://feed.test/rss",
        guid="post-1",
        link="https://feed.test/post-1",
        title=title,
        published_at=datetime(2026, 9, 8, 18, 0, tzinfo=UTC),
        content="image tt18546730-SHD.jpg",
    )


def setup(tmp_path):
    cfg = config(tmp_path)
    storage = Storage(cfg.database_path)
    storage.initialize()
    renderer = Renderer(storage, cfg.output_path, cfg.timezone)
    return cfg, storage, renderer


def release_views(html: str) -> tuple[str, str]:
    content = html.split('<section class="view" id="overview-view"', 1)[1]
    return content.split('<section class="view" id="history-view"', 1)


def test_season_release_is_current_until_all_expected_episodes_exist(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    for episode in range(1, 8):
        library.add_episode(series.id, 3, episode)
    jellyfin = Jellyfin(library, {(series.id, 3): set(range(1, 11))})
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([release()]))

    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 1
    assert row["jellyfin_episode_count"] == 7
    assert row["jellyfin_expected_episode_count"] == 10
    assert row["is_new"] == 1

    complete_library = Library([series], missing_episode_tracking_enabled=True)
    for episode in range(1, 11):
        complete_library.add_episode(series.id, 3, episode)
    scanner.jellyfin = Jellyfin(complete_library, {(series.id, 3): set(range(1, 11))})
    scanner.feeds = Feeds([])
    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 0
    assert row["jellyfin_episode_count"] == 10
    assert row["jellyfin_expected_episode_count"] == 10
    assert row["is_new"] == 0


def test_concrete_episode_resolves_only_when_exact_episode_exists(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    library.add_episode(series.id, 3, 8)
    jellyfin = Jellyfin(library, {(series.id, 3): set(range(1, 11))})
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        jellyfin,
        Feeds([release("The.Walking.Dead.Dead.City.S03E07.German")]),
    )

    assert scanner.run()
    assert storage.announcements()[0]["is_current"] == 1

    library.add_episode(series.id, 3, 7)
    assert scanner.run()
    assert storage.announcements()[0]["is_current"] == 0


def test_season_range_creates_independent_entries_and_statuses(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    for episode in (1, 2):
        library.add_episode(series.id, 3, episode)
    library.add_episode(series.id, 4, 1)
    expected = {
        (series.id, 3): {1, 2},
        (series.id, 4): {1, 2},
        (series.id, 5): {1, 2},
    }
    played = {(series.id, 5): {1, 2}}
    ranged = release(
        "The.Walking.Dead.Dead.City.S03.-.S06.Complete.German.1080p-WAYNE"
    )
    jellyfin = Jellyfin(library, expected, played=played)
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([ranged]))

    assert scanner.run()
    rows = {row["season"]: row for row in storage.announcements()}
    assert set(rows) == {3, 4, 5, 6}
    assert {row["feed_item_key"] for row in rows.values()} == {
        next(iter(rows.values()))["feed_item_key"]
    }
    assert len({row["source_key"] for row in rows.values()}) == 4
    assert all(row["link"] == ranged.link for row in rows.values())
    assert not rows[3]["is_current"]
    assert rows[3]["status_reason"] == "available"
    assert rows[4]["is_current"]
    assert rows[4]["needed_episodes"] == [2]
    assert not rows[5]["is_current"]
    assert rows[5]["status_reason"] == "played"
    assert rows[6]["is_current"]
    assert rows[6]["jellyfin_expected_episode_count"] is None
    assert jellyfin.series_calls == [series.id]

    html = cfg.output_path.read_text(encoding="utf-8")
    current_html, history_html = release_views(html)
    assert "The Walking Dead: Dead City · S04" in current_html
    assert "The Walking Dead: Dead City · S06" in current_html
    assert "The Walking Dead: Dead City · S03" not in current_html
    assert "The Walking Dead: Dead City · S05" not in current_html
    for season in range(3, 7):
        assert f"The Walking Dead: Dead City · S{season:02d}" in history_html


def test_changed_season_range_removes_obsolete_derived_entries(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    expected = {
        (series.id, season): {1, 2}
        for season in range(3, 7)
    }
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library, expected),
        Feeds([release("The.Walking.Dead.Dead.City.S03-S06.Complete.German")]),
    )

    assert scanner.run()
    assert {row["season"] for row in storage.announcements()} == {3, 4, 5, 6}
    assert scanner.run()
    assert len(storage.announcements()) == 4

    scanner.feeds = Feeds(
        [release("The.Walking.Dead.Dead.City.S03-S05.Complete.German")]
    )
    assert scanner.run()
    assert {row["season"] for row in storage.announcements()} == {3, 4, 5}


def test_range_quality_variants_are_grouped_once_per_season(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    expected = {
        (series.id, 3): {1},
        (series.id, 4): {1},
    }
    first = release("The.Walking.Dead.Dead.City.S03-S04.German.720p-WAYNE")
    second = replace(
        first,
        guid="post-2",
        link="https://feed.test/post-2",
        title="The.Walking.Dead.Dead.City.S03-S04.German.1080p-WvF",
    )
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library, expected),
        Feeds([first, second]),
    )

    assert scanner.run()
    assert len(storage.announcements()) == 4
    html = cfg.output_path.read_text(encoding="utf-8")
    current_html, _ = release_views(html)
    assert current_html.count('data-label="Release"') == 2
    for season in (3, 4):
        assert f"The Walking Dead: Dead City · S{season:02d}" in current_html
    assert current_html.count(">720p</a>") == 2
    assert current_html.count(">1080p</a>") == 2


def test_unknown_season_inventory_stays_current(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=False)
    for episode in range(1, 11):
        library.add_episode(series.id, 3, episode)
    jellyfin = Jellyfin(library)
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([release()]))

    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 1
    assert row["jellyfin_episode_count"] == 10
    assert row["jellyfin_expected_episode_count"] is None
    assert storage.state()["scan_status"] == "warning"
    assert jellyfin.series_calls == [series.id]


def test_season_api_error_stays_current(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    library.add_episode(series.id, 3, 1)
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library, error=JellyfinError("kaputt")),
        Feeds([release("The.Walking.Dead.Dead.City.S03.COMPLETED.German")]),
    )

    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 1
    assert row["jellyfin_expected_episode_count"] is None
    assert "Jellyfin-Sollzahl" in storage.state()["feed_errors"]


def test_contradictory_season_inventory_stays_unknown(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    library.add_episode(series.id, 3, 7)
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library, {(series.id, 3): {1, 2, 3}}),
        Feeds([release()]),
    )

    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 1
    assert row["jellyfin_expected_episode_count"] is None
    assert "widersprüchliche Episodendaten" in storage.state()["feed_errors"]


@pytest.mark.parametrize("marker", ["S03", "S03E02"])
def test_release_variants_stay_stored_but_are_grouped_in_current_view(
    tmp_path, marker
) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    jellyfin = Jellyfin(library, {(series.id, 3): set(range(1, 11))})
    first = release(f"The.Walking.Dead.Dead.City.{marker}.German.720p-WAYNE")
    second = replace(
        first,
        guid="post-2",
        link="https://feed.test/post-2",
        title=f"The.Walking.Dead.Dead.City.{marker}.German.1080p-WvF",
        published_at=datetime(2026, 9, 9, 18, 0, tzinfo=UTC),
    )
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([first, second]))

    assert scanner.run()
    assert len(storage.announcements()) == 2
    assert jellyfin.series_calls == [series.id]
    html = cfg.output_path.read_text(encoding="utf-8")
    current_html, history_html = release_views(html)
    assert current_html.count('data-label="Release"') == 1
    assert "1 Einträge" in current_html
    assert f">The Walking Dead: Dead City · {marker}</span>" in current_html
    assert ">720p</a>" in current_html
    assert ">1080p</a>" in current_html
    assert 'href="https://feed.test/post-1"' in current_html
    assert 'href="https://feed.test/post-2"' in current_html
    assert current_html.index(">720p</a>") < current_html.index(">1080p</a>")
    assert history_html.count('data-label="Eintrag"') == 2
    assert history_html.count(f">The Walking Dead: Dead City · {marker}</a>") == 2
    assert f'title="{first.title}"' in history_html
    assert f'title="{second.title}"' in history_html
    for section in (current_html, history_html):
        assert section.count("<th class=") == 4
        assert "Jellyfin-Serie" not in section
    assert "2 Einträge" in history_html


def test_open_imports_and_transfers_render_in_separate_views_with_timeline(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(
            Library([series], missing_episode_tracking_enabled=True),
            {(series.id, 3): {1, 2}},
        ),
        Feeds([release()]),
    )
    assert scanner.run()

    published = release().published_at
    for source, transferred_at in (
        ("older.mkv", published - timedelta(days=1)),
        ("newer.mkv", published + timedelta(days=1)),
    ):
        storage.observe_media_import(source, source, transferred_at)
        storage.update_media_import(
            source,
            "transferred",
            "Übernommen",
            parsed_title="Show",
            season=1,
            episode=2,
            target_path=f"Show/Staffel 01/{source}",
            transferred_at=transferred_at,
        )
    for source, status in (
        ("waiting.mkv", "waiting"),
        ("blocked.mkv", "blocked"),
        ("selection.mkv", "needs_selection"),
    ):
        storage.observe_media_import(source, source, published)
        storage.update_media_import(source, status, "Prüfung nötig")

    renderer.render()
    html = cfg.output_path.read_text(encoding="utf-8")
    media_html = html.split('id="media-import-view"', 1)[1].split("</section>", 1)[0]
    history_html = html.split('id="history-view"', 1)[1].split("</section>", 1)[0]

    assert "3 Einträge" in media_html
    assert all(
        source in media_html
        for source in ("waiting.mkv", "blocked.mkv", "selection.mkv")
    )
    assert "older.mkv" not in media_html and "newer.mkv" not in media_html
    assert "3 Einträge" in history_html
    assert (
        history_html.index("newer.mkv")
        < history_html.index("The Walking Dead: Dead City")
        < history_html.index("older.mkv")
    )
    assert history_html.count('class="type-marker"') == 3
    assert "Show/Staffel 01/newer.mkv" in history_html
    assert "S01E02" in history_html
    assert "Übernommen" in history_html
    assert "waiting.mkv" not in history_html


def test_ui_labels_and_link_states_render_consistently(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    renderer.media_import_enabled = True
    renderer.render()
    html = cfg.output_path.read_text(encoding="utf-8")
    nav = html.split('<nav class="nav"', 1)[1].split("</nav>", 1)[0]

    assert (
        nav.index(">Feed</a>")
        < nav.index(">Medienimport</a>")
        < nav.index(">Historie</a>")
        < nav.index(">Log</a>")
    )
    assert "Download jetzt scannen" in html
    assert "Download ist leer" in html
    assert "Keine offenen Importe" in html
    assert 'class="section-note"' not in html
    assert "--link: #53e4d3" in html
    assert "--visited: #c4a0f7" in html
    assert ".release a:visited { color: var(--visited); }" in html
    assert ".variant-links a:visited { color: var(--visited);" in html

    selection_html = renderer.render_selection(
        SimpleNamespace(source_path="show.mkv", signature="signature", choices=())
    )
    assert "Download: show.mkv" in selection_html
    assert "a:visited { color: var(--visited); }" in selection_html
    assert "Die Auswahl importiert alle aktuell gefundenen Folgen" in selection_html


def test_current_grouping_key_and_aggregated_fields() -> None:
    def row(
        source_key,
        *,
        feed_url="https://feed.test/rss",
        series_id="show",
        season=3,
        episode=None,
        title="Show.S03.1080p-WAYNE",
        published_at="2026-09-08T18:00:00+00:00",
        is_new=0,
        match_warning=0,
    ):
        return {
            "source_key": source_key,
            "feed_url": feed_url,
            "matched_series_id": series_id,
            "matched_series_name": "Show",
            "season": season,
            "episode": episode,
            "title": title,
            "link": f"https://feed.test/{source_key}",
            "parsed_title": "Show",
            "published_at": published_at,
            "first_seen_at": published_at,
            "is_new": is_new,
            "is_current": 1,
            "match_warning": match_warning,
        }

    groups = group_current_releases(
        [
            row("old", is_new=1),
            row(
                "new",
                title="Show.S03.1080p-WvF",
                published_at="2026-09-09T18:00:00+00:00",
                match_warning=1,
            ),
            row("other-feed", feed_url="https://other.test/rss"),
            row("other-season", season=4),
            row("episode", episode=1),
        ]
    )

    assert len(groups) == 4
    grouped = next(group for group in groups if len(group["variants"]) == 2)
    assert grouped["published_at"] == "2026-09-09T18:00:00+00:00"
    assert grouped["is_new"]
    assert grouped["match_warning"]
    assert [variant["label"] for variant in grouped["variants"]] == [
        "1080p · WAYNE",
        "1080p · WvF",
    ]


def test_unknown_quality_links_are_numbered() -> None:
    rows = []
    for number in (1, 2):
        rows.append(
            {
                "feed_url": "https://feed.test/rss",
                "matched_series_id": "show",
                "matched_series_name": "Show",
                "season": 3,
                "episode": None,
                "title": f"Show.S03.Source-{number}",
                "link": f"https://feed.test/{number}",
                "parsed_title": "Show",
                "published_at": f"2026-09-0{number}T18:00:00+00:00",
                "first_seen_at": f"2026-09-0{number}T18:00:00+00:00",
                "is_new": 0,
                "is_current": 1,
                "match_warning": 0,
            }
        )

    variants = group_current_releases(rows)[0]["variants"]

    assert [variant["label"] for variant in variants] == ["Quelle 1", "Quelle 2"]


def test_html_is_escaped_and_keeps_reduced_columns(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("show", "Show", imdb_id="tt1234567")
    library = Library([series], missing_episode_tracking_enabled=True)
    unsafe = FeedRelease(
        feed_url="https://feed.test/rss",
        guid="unsafe",
        link="https://feed.test/post",
        title="Show.S01.<script>alert(1)</script>",
        published_at=datetime(2026, 9, 8, tzinfo=UTC),
        content="tt1234567",
    )
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library, {(series.id, 1): {1, 2}}),
        Feeds([unsafe]),
    )

    assert scanner.run()
    html = cfg.output_path.read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "Aktuell fehlend" in html
    assert "Historie" in html
    assert '<section class="view" id="history-view"' in html
    assert '<section class="view" id="media-import-view"' in html
    assert 'href="#history"' in html
    assert 'href="#media-import"' in html
    assert '<html lang="de-CH">' in html
    assert 'rel="icon"' in html
    assert 'href="/favicon.svg"' in html
    favicon = cfg.output_path.with_name("favicon.svg").read_text(encoding="utf-8")
    assert favicon.startswith("<svg ")
    assert "Qualität" not in html
    assert 'id="myInput"' not in html
    assert "Erkannt aus" not in html
    assert "Jellyfin Release Monitor" not in html
    assert "Neu im letzten Scan" not in html
    assert "Letzter Erfolg" not in html
    assert ">Quelle</a>" in html
    assert "IMDb-ID" not in html
    assert "a:visited" in html
    assert html.count("<th ") == 8
