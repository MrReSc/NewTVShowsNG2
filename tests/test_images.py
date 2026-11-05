from __future__ import annotations

import http.client
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from newtvshowsng2.images import PLACEHOLDER, SeriesImageCache, series_image_url
from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.models import FeedRelease, Library, Match, Series
from newtvshowsng2.parsing import parse_release
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.server import ApplicationServer
from newtvshowsng2.storage import Storage

SERIES_ID = "13008790f7b713e88c6e2b63430658a7"


class Jellyfin:
    def __init__(self):
        self.calls = []
        self.catalogue_calls = 0
        self.series = [Series(SERIES_ID, "MobLand")]
        self.result = (b"poster", "image/jpeg")
        self.error = False

    def load_series(self):
        self.catalogue_calls += 1
        if self.error:
            raise JellyfinError("offline")
        return self.series[:]

    def load_primary_image(self, series_id):
        self.calls.append(series_id)
        if self.error:
            raise JellyfinError("offline")
        return self.result


def test_cache_shares_concurrent_requests_and_refreshes_after_expiry():
    jellyfin = Jellyfin()
    now = [0]
    cache = SeriesImageCache(jellyfin, clock=lambda: now[0])
    with ThreadPoolExecutor(max_workers=8) as executor:
        images = list(executor.map(lambda _: cache.get(series_id=SERIES_ID), range(16)))
    assert all(image.content == b"poster" for image in images)
    assert jellyfin.calls == [SERIES_ID]
    now[0] = 1800
    assert cache.get(series_id=SERIES_ID).max_age == 1800
    now[0] = 3600
    jellyfin.result = (b"new poster", "image/jpeg")
    assert cache.get(series_id=SERIES_ID).content == b"new poster"
    assert jellyfin.calls == [SERIES_ID, SERIES_ID]


@pytest.mark.parametrize("failure", ["missing", "offline"])
def test_placeholder_is_retried_after_one_minute(failure):
    jellyfin = Jellyfin()
    jellyfin.result = None
    jellyfin.error = failure == "offline"
    now = [0]
    cache = SeriesImageCache(jellyfin, clock=lambda: now[0])
    assert cache.get(series_id=SERIES_ID).content == PLACEHOLDER
    now[0] = 59
    assert cache.get(series_id=SERIES_ID).max_age == 1
    assert len(jellyfin.calls) == 1
    now[0] = 60
    jellyfin.error = False
    jellyfin.result = (b"available", "image/jpeg")
    assert cache.get(series_id=SERIES_ID).content == b"available"


def test_lru_cache_limits_entries_and_bytes():
    jellyfin = Jellyfin()
    cache = SeriesImageCache(jellyfin, max_entries=2, max_bytes=12)
    first, second, third = (str(number) * 32 for number in (1, 2, 3))
    cache.get(series_id=first)
    cache.get(series_id=second)
    cache.get(series_id=first)
    cache.get(series_id=third)
    cache.get(series_id=second)
    assert jellyfin.calls == [first, second, third, second]
    jellyfin.result = (b"x" * 13, "image/jpeg")
    cache.get(series_id=first)
    cache.get(series_id=first)
    assert jellyfin.calls[-2:] == [first, first]


def test_cache_evicts_for_byte_limit_before_entry_limit():
    jellyfin = Jellyfin()
    cache = SeriesImageCache(jellyfin, max_entries=10, max_bytes=9)
    cache.get(series_id="1" * 32)
    cache.get(series_id="2" * 32)
    cache.get(series_id="1" * 32)
    assert jellyfin.calls == ["1" * 32, "2" * 32, "1" * 32]


def test_import_poster_lookup_uses_fresh_catalogue_and_rejects_ambiguity():
    jellyfin = Jellyfin()
    now = [0]
    cache = SeriesImageCache(jellyfin, clock=lambda: now[0])
    assert cache.get(title="MobLand.S01").content == b"poster"
    assert jellyfin.catalogue_calls == 1
    assert cache.get(title="MobLand.S01").content == b"poster"
    assert jellyfin.catalogue_calls == 1
    now[0] = 3600
    jellyfin.series.append(Series("2" * 32, "MobLand"))
    assert cache.get(title="MobLand.S01").content == PLACEHOLDER
    assert jellyfin.catalogue_calls == 2
    assert jellyfin.calls == [SERIES_ID]


@pytest.mark.parametrize("name", ["Unknown", "MobLad"])
def test_missing_and_fuzzy_import_matches_use_placeholder(name):
    jellyfin = Jellyfin()
    cache = SeriesImageCache(jellyfin)
    assert cache.get(title=f"{name}.S01").content == PLACEHOLDER
    assert jellyfin.calls == []


def test_image_urls_include_only_local_identifiers_and_search_titles():
    assert series_image_url({"matched_series_id": SERIES_ID}) == f"/series-image?id={SERIES_ID}"
    assert series_image_url({"matched_series_id": SERIES_ID, "match_warning": True}) == "/series-placeholder.svg"
    assert series_image_url({"matched_series_id": "../../file"}) == "/series-placeholder.svg"
    assert series_image_url({"kind": "import"}) == "/series-placeholder.svg"
    url = series_image_url({"kind": "import", "parsed_title": "A & B", "season": 2})
    assert parse_qs(urlsplit(url).query) == {"title": ["A & B.S02"]}


def test_render_includes_small_posters_in_both_views_and_import_history(tmp_path):
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    now = datetime(2026, 11, 5, tzinfo=UTC)
    show = Series(SERIES_ID, "MobLand")
    title = "MobLand.S01E02.German.1080p"
    release = FeedRelease("https://feed.test/rss", "guid", "https://feed.test/show", title, now)
    storage.upsert_release(release, parse_release(title), Match(show, "Titel"), Library([show]), now)
    storage.observe_media_import("MobLand.S01E01.mkv", "signature", now)
    storage.update_media_import("MobLand.S01E01.mkv", "transferred", "Übernommen", parsed_title="MobLand", season=1, episode=1, transferred_at=now)
    output = tmp_path / "index.html"
    Renderer(storage, output, "Europe/Zurich").render()
    html = output.read_text()
    overview = html.split('id="overview-view"')[1].split('id="history-view"')[0]
    history = html.split('id="history-view"')[1]
    assert overview.count('class="series-poster"') == 1
    assert history.count('class="series-poster"') == 2
    assert f'src="/series-image?id={SERIES_ID}"' in overview
    assert 'src="/series-image?title=MobLand.S01"' in history
    assert 'width="56" height="84" alt="" loading="lazy"' in overview


def test_server_proxies_posters_and_handles_invalid_requests_without_jellyfin_writes(tmp_path):
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    jellyfin = Jellyfin()
    server = ApplicationServer(
        ("127.0.0.1", 0), tmp_path / "index.html", storage,
        tmp_path / "app.log", "Europe/Zurich", images=SeriesImageCache(jellyfin),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def get(path):
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        connection.request("GET", path)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    try:
        status, headers, body = get(f"/series-image?id={SERIES_ID}")
        assert status == 200 and body == b"poster"
        assert headers["Content-Type"] == "image/jpeg"
        assert headers["Cache-Control"] == "private, max-age=3600"
        assert headers["X-Content-Type-Options"] == "nosniff"
        for query in ("", "url=http://other.test", "id=bad", "id=", "id=../file", f"id={SERIES_ID}&title=MobLand.S01", f"id={SERIES_ID}&id={SERIES_ID}", "title=invalid", "title=" + "x" * 513):
            assert get("/series-image?" + query)[0] == 400
        assert jellyfin.calls == [SERIES_ID]
        status, headers, body = get("/series-placeholder.svg")
        assert status == 200 and body == PLACEHOLDER
        assert headers["Cache-Control"] == "private, max-age=60"
        jellyfin.error = True
        assert get("/series-image?id=" + "2" * 32)[2] == PLACEHOLDER
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
