from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from newtvshowsng2.config import Config
from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.models import FeedRelease, Library, Series
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.storage import Storage


class Jellyfin:
    def __init__(self, library, expected=None, error=None):
        self.library = library
        self.expected = expected or {}
        self.error = error
        self.season_calls = []

    def load_library(self):
        return self.library

    def load_season_episodes(self, series_id, season):
        self.season_calls.append((series_id, season))
        if self.error:
            raise self.error
        return set(self.expected[(series_id, season)])


class Feeds:
    def __init__(self, releases):
        self.releases = releases

    def load(self, _url):
        return self.releases


def config(tmp_path: Path) -> Config:
    return Config(
        jellyfin_url="http://jellyfin.test",
        jellyfin_api_key="secret",
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
    assert jellyfin.season_calls == []


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


def test_release_variants_remain_separate(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series], missing_episode_tracking_enabled=True)
    jellyfin = Jellyfin(library, {(series.id, 3): set(range(1, 11))})
    first = release("The.Walking.Dead.Dead.City.S03.German.720p")
    second = replace(
        first,
        guid="post-2",
        link="https://feed.test/post-2",
        title="The.Walking.Dead.Dead.City.S03.German.1080p",
    )
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([first, second]))

    assert scanner.run()
    assert len(storage.announcements()) == 2
    assert jellyfin.season_calls == [(series.id, 3)]


def test_html_is_escaped_and_has_no_quality_ui(tmp_path) -> None:
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
    assert '<details class="history">' in html
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
    assert "Quelle" not in html
    assert "IMDb-ID" not in html
    assert "a:visited" in html
    assert html.count("<th ") == 10
