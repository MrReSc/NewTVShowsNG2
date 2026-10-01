from __future__ import annotations

import http.client
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime
from urllib.parse import quote, urlencode

import pytest

from newtvshowsng2.media_importer import SelectionUnavailable
from newtvshowsng2.models import Library, RemoteSeries, Series
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.server import ApplicationServer
from test_media_importer import Jellyfin, release_folder, setup


class LiveJellyfin(Jellyfin):
    def __init__(self, remotes):
        super().__init__(remotes)
        self.library = Library([])

    def load_library(self):
        return self.library


def _prepare(tmp_path):
    remotes = [
        RemoteSeries(
            "Eine Billion Dollar", 2023,
            (("Tmdb", "234717"), ("Imdb", "tt26456880"), ("Tvdb", "440104")),
        ),
        RemoteSeries("Eine Billion Dollar", 2023, (("Imdb", "tt26747258"),)),
    ]
    jellyfin = LiveJellyfin(remotes)
    config, storage, importer = setup(tmp_path, jellyfin)
    sources = [
        release_folder(config.income_dir, f"Eine.Billion.Dollar.S01E0{number}.German")
        for number in (1, 2)
    ]
    unrelated = release_folder(config.income_dir, "Other.Show.S01E01.German")
    importer.run(Library([]), datetime(2026, 9, 29, tzinfo=UTC), force=True)
    return config, storage, importer, jellyfin, sources, unrelated


def test_one_selection_imports_whole_series_and_waits_for_jellyfin(tmp_path) -> None:
    config, storage, importer, jellyfin, sources, unrelated = _prepare(tmp_path)
    options = importer.selection_options(sources[0].name)
    assert len(options.choices) == 2
    assert options.choices[0].imdb_url == "https://www.imdb.com/title/tt26456880/"
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[0].key
    )

    result = importer.run(Library([]), force=True, selection=selected)
    assert result.transferred == 2
    assert unrelated.exists()
    assert storage.media_import(unrelated.name)["status"] == "blocked"
    target = config.shows_dir / "Eine Billion Dollar (2023) [imdbid-tt26456880]"
    assert (target / "Staffel 01" / sources[0].name).exists()
    assert (target / "Staffel 01" / sources[1].name).exists()
    assert jellyfin.refresh_calls == 1

    later = release_folder(config.income_dir, "Eine.Billion.Dollar.S01E03.German")
    waiting = importer.run(Library([]), force=True)
    assert waiting.waiting == 1
    assert storage.media_import(later.name)["status"] == "waiting"
    assert "Jellyfin-Bibliothekseintrag" in storage.media_import(later.name)["reason"]
    assert later.exists()

    series = Series(
        "series-1", "Eine Billion Dollar", production_year=2023,
        imdb_id="tt26456880", path="/media/tv/" + target.name,
        provider_ids=(("Tmdb", "234717"), ("Imdb", "tt26456880")),
    )
    assert importer.run(Library([series]), force=True).transferred == 1
    assert (target / "Staffel 01" / later.name).exists()


def test_stale_source_or_changed_jellyfin_result_rejects_selection(tmp_path) -> None:
    config, _, importer, jellyfin, sources, _ = _prepare(tmp_path)
    options = importer.selection_options(sources[0].name)
    source_video = next(sources[0].glob("*.mkv"))
    source_video.write_bytes(b"changed")
    with pytest.raises(SelectionUnavailable, match="verändert"):
        importer.select_series(
            options.source_path, options.signature, options.choices[0].key
        )
    assert not list(config.shows_dir.iterdir())

    source_video.write_bytes(b"episode")
    importer.run(Library([]), force=True)
    options = importer.selection_options(sources[0].name)
    jellyfin.remote[0] = RemoteSeries(
        "Eine Billion Dollar", 2023, (("Tmdb", "999999"),)
    )
    with pytest.raises(SelectionUnavailable, match="Suchergebnis"):
        importer.select_series(
            options.source_path, options.signature, options.choices[0].key
        )


def test_source_change_after_choice_stops_selected_run_before_moving(tmp_path) -> None:
    config, _, importer, _, sources, _ = _prepare(tmp_path)
    options = importer.selection_options(sources[1].name)
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[0].key
    )
    next(sources[1].glob("*.mkv")).write_bytes(b"new content")

    with pytest.raises(SelectionUnavailable, match="verändert"):
        importer.run(Library([]), force=True, selection=selected)
    assert all(source.exists() for source in sources)
    assert not list(config.shows_dir.iterdir())


def test_choice_without_imdb_link_remains_selectable_and_conflicts_block(tmp_path) -> None:
    config, storage, importer, jellyfin, sources, _ = _prepare(tmp_path)
    jellyfin.remote[1] = RemoteSeries(
        "Eine Billion Dollar", 2023, (("Tvdb", "123456"),)
    )
    options = importer.selection_options(sources[0].name)
    html = Renderer(storage, config.output_path, config.timezone, True).render_selection(options)
    assert html.count("Auf IMDb prüfen") == 1
    assert "kein IMDb-Link verfügbar" in html
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[1].key
    )
    target = config.shows_dir / "Eine Billion Dollar (2023) [tvdbid-123456]"
    (target / "Staffel 01" / "other.mkv").parent.mkdir(parents=True)
    (target / "Staffel 01" / "other.mkv").write_bytes(b"existing")

    result = importer.run(Library([]), force=True, selection=selected)
    assert result.blocked == 2
    assert all(source.exists() for source in sources)
    assert (target / "Staffel 01" / "other.mkv").read_bytes() == b"existing"
    assert jellyfin.refresh_calls == 0


def test_second_distinct_selection_waits_for_first_import(tmp_path) -> None:
    first_refresh_started = threading.Event()
    allow_first_refresh = threading.Event()

    class BlockingRefreshJellyfin(LiveJellyfin):
        def refresh_library(self):
            self.refresh_calls += 1
            if self.refresh_calls == 1:
                first_refresh_started.set()
                assert allow_first_refresh.wait(timeout=3)

    jellyfin = BlockingRefreshJellyfin([
        RemoteSeries("Alpha Show", 2026, (("Imdb", "tt0000001"),)),
        RemoteSeries("Alpha Show", 2026, (("Imdb", "tt0000002"),)),
        RemoteSeries("Beta Show", 2026, (("Imdb", "tt0000003"),)),
        RemoteSeries("Beta Show", 2026, (("Imdb", "tt0000004"),)),
    ])
    config, storage, importer = setup(tmp_path, jellyfin)
    first_source = release_folder(config.income_dir, "Alpha.Show.S01E01.German")
    second_source = release_folder(config.income_dir, "Beta.Show.S01E01.German")
    importer.run(Library([]), datetime(2026, 9, 29, tzinfo=UTC), force=True)
    first_options = importer.selection_options(first_source.name)
    second_options = importer.selection_options(second_source.name)

    def selection_body(options, imdb_id):
        choice = next(
            item for item in options.choices
            if ("Imdb", imdb_id) in item.remote.provider_ids
        )
        return urlencode({
            "source": options.source_path,
            "signature": options.signature,
            "choice": choice.key,
        })

    renderer = Renderer(storage, config.output_path, config.timezone, True)
    renderer.render()
    scanner = Scanner(config, storage, renderer, jellyfin, object(), importer)
    second_start_attempted = threading.Event()
    start_selected_import = scanner.start_selected_import

    def track_second_start(source_path, signature, choice_key):
        if source_path == second_source.name:
            second_start_attempted.set()
        return start_selected_import(source_path, signature, choice_key)

    scanner.start_selected_import = track_second_start
    server = ApplicationServer(
        ("127.0.0.1", 0), config.output_path, storage, config.log_path,
        config.timezone, scanner,
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    headers = {"Origin": origin, "Content-Type": "application/x-www-form-urlencoded"}

    def post(body):
        connection = http.client.HTTPConnection(*server.server_address, timeout=5)
        try:
            connection.request("POST", "/run/import/resolve", body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.getheader("Location"), response.read().decode()
        finally:
            connection.close()

    second_response = []
    second_done = threading.Event()

    def post_second_selection():
        try:
            second_response.append(post(selection_body(second_options, "tt0000003")))
        finally:
            second_done.set()

    try:
        assert post(selection_body(first_options, "tt0000001"))[:2] == (
            303, "/#media-import"
        )
        assert first_refresh_started.wait(timeout=3)
        second_thread = threading.Thread(target=post_second_selection)
        second_thread.start()
        assert second_start_attempted.wait(timeout=3)
        assert not second_done.wait(timeout=0.1)

        allow_first_refresh.set()
        assert second_done.wait(timeout=3)
        second_thread.join(timeout=3)
        assert second_response[0][:2] == (303, "/#media-import")

        deadline = time.monotonic() + 3
        while scanner._lock.locked() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not scanner._lock.locked()
        assert storage.state()["manual_import_status"] == "ok"
        assert not first_source.exists()
        assert not second_source.exists()
    finally:
        allow_first_refresh.set()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=3)


def test_selection_page_endpoints_and_schedule(tmp_path) -> None:
    config, storage, importer, jellyfin, sources, _ = _prepare(tmp_path)
    next_run = datetime(2026, 10, 1, tzinfo=UTC)
    storage.begin_scan(datetime(2026, 9, 29, tzinfo=UTC), next_run)
    storage.complete_scan(datetime(2026, 9, 29, tzinfo=UTC), next_run, [])
    renderer = Renderer(storage, config.output_path, config.timezone, True)
    renderer.render()
    html = config.output_path.read_text()
    assert "Serienzuordnung wählen" in html
    assert "/media-import/resolve?source=" in html
    scanner = Scanner(config, storage, renderer, jellyfin, object(), importer)
    server = ApplicationServer(
        ("127.0.0.1", 0), config.output_path, storage, config.log_path,
        config.timezone, scanner,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.getheader("Location"), response.read().decode()
        finally:
            connection.close()

    try:
        source = sources[0].name
        status, _, page = request(
            "GET", "/media-import/resolve?source=" + quote(source)
        )
        assert status == 200
        assert "tt26456880" in page and "tt26747258" in page
        assert "https://www.imdb.com/title/tt26456880/" in page
        options = importer.selection_options(source)
        body = urlencode({
            "source": source, "signature": options.signature,
            "choice": options.choices[0].key,
        })
        origin = f"http://127.0.0.1:{server.server_address[1]}"
        headers = {"Origin": origin, "Content-Type": "application/x-www-form-urlencoded"}
        assert request("POST", "/run/import/resolve", body, {**headers, "Origin": "http://foreign.test"})[0] == 403
        stale_body = urlencode({
            "source": source, "signature": "outdated", "choice": options.choices[0].key,
        })
        assert request("POST", "/run/import/resolve", stale_body, headers)[0] == 409
        assert all(item.exists() for item in sources)
        assert request("POST", "/run/import/resolve", body, headers)[:2] == (303, "/#media-import")
        deadline = time.monotonic() + 3
        while scanner._lock.locked() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not scanner._lock.locked()
        assert storage.state()["manual_import_status"] == "ok"
        assert not sources[0].exists() and not sources[1].exists()
        assert storage.state()["next_run_at"] == next_run.isoformat()
        scanner.config = replace(config, media_import_enabled=False)
        assert request("GET", "/media-import/resolve?source=" + quote(source))[0] == 404
        assert request("POST", "/run/import/resolve", body, headers)[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
