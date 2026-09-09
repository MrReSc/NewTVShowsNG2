from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from newtvshowsng2.config import Config
from newtvshowsng2.models import FeedRelease, Library, Series
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.storage import Storage


class Jellyfin:
    def __init__(self, library):
        self.library = library

    def load_library(self):
        return self.library


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


def test_season_release_stays_current_until_newer_season(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series])
    library.add_episode(series.id, 3, 6)
    scanner = Scanner(cfg, storage, renderer, Jellyfin(library), Feeds([release()]))

    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 1
    assert row["jellyfin_episode"] == 6
    assert row["is_new"] == 1

    newer_library = Library([series])
    newer_library.add_episode(series.id, 4, 1)
    scanner.jellyfin = Jellyfin(newer_library)
    assert scanner.run()
    row = storage.announcements()[0]
    assert row["is_current"] == 0
    assert row["is_new"] == 0


def test_concrete_episode_resolves_only_when_exact_episode_exists(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series])
    library.add_episode(series.id, 3, 8)
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library),
        Feeds([release("The.Walking.Dead.Dead.City.S03E07.German")]),
    )

    assert scanner.run()
    assert storage.announcements()[0]["is_current"] == 1

    library.add_episode(series.id, 3, 7)
    assert scanner.run()
    assert storage.announcements()[0]["is_current"] == 0


def test_release_variants_remain_separate(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("dead-city", "The Walking Dead: Dead City", imdb_id="tt18546730")
    library = Library([series])
    first = release("The.Walking.Dead.Dead.City.S03.German.720p")
    second = replace(
        first,
        guid="post-2",
        link="https://feed.test/post-2",
        title="The.Walking.Dead.Dead.City.S03.German.1080p",
    )
    scanner = Scanner(cfg, storage, renderer, Jellyfin(library), Feeds([first, second]))

    assert scanner.run()
    assert len(storage.announcements()) == 2


def test_html_is_escaped_and_has_no_quality_ui(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    series = Series("show", "Show", imdb_id="tt1234567")
    library = Library([series])
    unsafe = FeedRelease(
        feed_url="https://feed.test/rss",
        guid="unsafe",
        link="https://feed.test/post",
        title="Show.S01.<script>alert(1)</script>",
        published_at=datetime(2026, 9, 8, tzinfo=UTC),
        content="tt1234567",
    )
    scanner = Scanner(cfg, storage, renderer, Jellyfin(library), Feeds([unsafe]))

    assert scanner.run()
    html = cfg.output_path.read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "Aktuell fehlend" in html
    assert "Historie" in html
    assert '<html lang="de-CH">' in html
    assert 'rel="icon"' in html
    assert 'href="favicon.svg"' in html
    favicon = cfg.output_path.with_name("favicon.svg").read_text(encoding="utf-8")
    assert favicon.startswith("<svg ")
    assert "Qualität" not in html
    assert 'id="myInput"' not in html
