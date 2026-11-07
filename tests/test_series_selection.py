from __future__ import annotations

import http.client
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlencode

import pytest

from newtvshowsng2.jellyfin import JellyfinError
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


def _prepare_title_mismatch(
    tmp_path, folder_name="Dark Matter Der Zeitenläufer (2026) [imdbid-tt19231492]"
):
    remote = RemoteSeries(
        "Dark Matter (2024)", 2024,
        (("Imdb", "tt19231492"), ("Tmdb", "196322"), ("Tvdb", "393159")),
    )
    jellyfin = LiveJellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    season_path = config.shows_dir / folder_name / "Staffel 02"
    season_path.mkdir(parents=True)
    release_folder(season_path, "Dark.Matter.Der.Zeitenlaeufer.S02E09.German")
    jellyfin.library = Library([
        Series(
            "dark-matter", "Dark Matter (2024)", original_title="Dark Matter (2024)",
            production_year=2024, imdb_id="tt19231492",
            path="/media/tv/" + folder_name, provider_ids=remote.provider_ids,
        ),
    ])
    sources = [
        release_folder(config.income_dir, f"Dark.Matter.Der.Zeitenlaeufer.S02E{number}.German")
        for number in (10, 11)
    ]
    unrelated = release_folder(config.income_dir, "Other.Show.S01E01.German")
    importer.run(jellyfin.library, force=True)
    return config, storage, importer, jellyfin, sources, unrelated


@pytest.mark.parametrize("folder_name", [
    "Dark Matter Der Zeitenläufer (2026) [imdbid-tt19231492]",
    "Unrelated directory name",
])
def test_title_mismatch_requires_confirmation_and_uses_jellyfin_path(
    tmp_path, folder_name
) -> None:
    config, storage, importer, jellyfin, sources, unrelated = _prepare_title_mismatch(
        tmp_path, folder_name
    )
    assert all(source.exists() for source in sources)
    assert all(storage.media_import(source.name)["status"] == "needs_selection" for source in sources)
    assert "Jellyfin-Titel weicht" in storage.media_import(sources[0].name)["reason"]

    options = importer.selection_options(sources[0].name)
    assert len(options.choices) == 1
    assert options.choices[0].existing_series.id == "dark-matter"
    html = Renderer(storage, config.output_path, config.timezone, True).render_selection(options)
    assert "Release-Titel: Dark.Matter.Der.Zeitenlaeufer" in html
    assert '<h2 id="choice-1">Dark Matter (2024)</h2>' in html
    assert "Serienjahr: 2024" in html
    assert "tt19231492" in html
    assert "Die Bestätigung gilt nur für diesen Import" in html
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[0].key
    )
    assert selected.existing_series_id == "dark-matter"

    result = importer.run(jellyfin.library, force=True, selection=selected)
    assert result.transferred == 2
    assert result.blocked == 0
    target = config.shows_dir / folder_name / "Staffel 02"
    assert all((target / source.name).is_dir() for source in sources)
    assert unrelated.exists()

    later = release_folder(config.income_dir, "Dark.Matter.Der.Zeitenlaeufer.S02E12.German")
    importer.run(jellyfin.library, force=True)
    assert later.exists()
    assert storage.media_import(later.name)["status"] == "needs_selection"


@pytest.mark.parametrize("duplicate_in_library", [False, True])
def test_confirmed_title_mismatch_keeps_existing_episode(
    tmp_path, duplicate_in_library
) -> None:
    config, storage, importer, jellyfin, sources, _ = _prepare_title_mismatch(tmp_path)
    options = importer.selection_options(sources[0].name)
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[0].key
    )
    target = config.shows_dir / Path(jellyfin.library.series[0].path).name / "Staffel 02"
    if duplicate_in_library:
        jellyfin.library.add_episode("dark-matter", 2, 10)
    else:
        release_folder(target, sources[0].name)
    result = importer.run(jellyfin.library, force=True, selection=selected)

    assert result.blocked == 1
    assert result.transferred == 1
    assert sources[0].exists()
    assert not sources[1].exists()
    assert "bereits" in storage.media_import(sources[0].name)["reason"]


@pytest.mark.parametrize("change", ["removed", "replaced", "conflicting", "ambiguous"])
def test_confirmed_title_mismatch_cannot_create_a_series(
    tmp_path, change
) -> None:
    config, storage, importer, jellyfin, sources, _ = _prepare_title_mismatch(tmp_path)
    options = importer.selection_options(sources[0].name)
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[0].key
    )
    series = jellyfin.library.series[0]
    if change == "removed":
        jellyfin.library.series = []
    elif change == "replaced":
        jellyfin.library.series = [replace(series, id="another-series")]
    elif change == "conflicting":
        jellyfin.library.series = [replace(
            series, imdb_id="tt9999999",
            provider_ids=(("Imdb", "tt9999999"), ("Tmdb", "196322")),
        )]
    else:
        jellyfin.library.series.append(replace(series, id="another-series"))
    result = importer.run(jellyfin.library, force=True, selection=selected)

    assert result.transferred == 0
    assert result.blocked == 2
    assert all(source.exists() for source in sources)
    assert all(storage.media_import(source.name)["status"] == "blocked" for source in sources)
    assert not (config.shows_dir / "Dark Matter (2024) (2024) [imdbid-tt19231492]").exists()


@pytest.mark.parametrize("change", ["source", "removed", "replaced", "conflicting"])
def test_title_mismatch_choice_is_revalidated_before_confirmation(tmp_path, change) -> None:
    _, _, importer, jellyfin, sources, _ = _prepare_title_mismatch(tmp_path)
    options = importer.selection_options(sources[0].name)
    if change == "source":
        next(sources[0].glob("*.mkv")).write_bytes(b"changed")
    elif change == "removed":
        jellyfin.library.series = []
    elif change == "conflicting":
        jellyfin.remote = [replace(
            jellyfin.remote[0], provider_ids=(("Imdb", "tt19231492"), ("Tmdb", "999999"))
        )]
    else:
        jellyfin.library.series = [replace(jellyfin.library.series[0], id="another-series")]
    with pytest.raises(SelectionUnavailable):
        importer.select_series(options.source_path, options.signature, options.choices[0].key)
    assert all(source.exists() for source in sources)


def test_title_mismatch_source_changed_after_confirmation_is_rejected(tmp_path) -> None:
    _, _, importer, jellyfin, sources, _ = _prepare_title_mismatch(tmp_path)
    options = importer.selection_options(sources[0].name)
    selected = importer.select_series(
        options.source_path, options.signature, options.choices[0].key
    )
    next(sources[0].glob("*.mkv")).write_bytes(b"changed")

    with pytest.raises(SelectionUnavailable, match="verändert"):
        importer.run(jellyfin.library, force=True, selection=selected)
    assert all(source.exists() for source in sources)


@pytest.mark.parametrize("change", [
    "no_results", "multiple_results", "unknown_provider", "no_provider", "ambiguous",
    "conflicting", "wrong_year",
])
def test_title_mismatch_fallback_is_limited_to_one_existing_series(tmp_path, change) -> None:
    _, storage, importer, jellyfin, sources, _ = _prepare_title_mismatch(tmp_path)
    if change == "no_results":
        jellyfin.remote = []
    elif change == "multiple_results":
        jellyfin.remote.append(RemoteSeries("Other Series", 2024, (("Imdb", "tt9999999"),)))
    elif change == "unknown_provider":
        jellyfin.remote = [replace(jellyfin.remote[0], provider_ids=(("Imdb", "tt9999999"),))]
    elif change == "no_provider":
        jellyfin.remote = [replace(jellyfin.remote[0], provider_ids=())]
    elif change == "ambiguous":
        jellyfin.library.series.append(replace(jellyfin.library.series[0], id="another-series"))
    elif change == "conflicting":
        jellyfin.remote = [replace(
            jellyfin.remote[0], provider_ids=(("Imdb", "tt19231492"), ("Tmdb", "999999"))
        )]
    else:
        sources.append(release_folder(
            importer.config.income_dir, "Dark.Matter.Der.Zeitenlaeufer.2026.S02E12.German"
        ))
    importer.run(jellyfin.library, force=True)

    checked = sources[-1] if change == "wrong_year" else sources[0]
    assert storage.media_import(checked.name)["status"] != "needs_selection"
    assert checked.exists()


def test_title_mismatch_lookup_failure_preserves_existing_wait(tmp_path, monkeypatch) -> None:
    _, storage, importer, jellyfin, sources, _ = _prepare_title_mismatch(tmp_path)

    def unavailable(*args, **kwargs):
        raise JellyfinError("offline")

    monkeypatch.setattr(jellyfin, "search_series", unavailable)
    result = importer.run(jellyfin.library, force=True)

    assert result.waiting == 2
    assert all(source.exists() for source in sources)
    for source in sources:
        row = storage.media_import(source.name)
        assert row["status"] == "waiting"
        assert "Wartet auf Jellyfin-Bibliothekseintrag" in row["reason"]


def test_one_selection_imports_whole_series_and_waits_for_jellyfin(tmp_path) -> None:
    config, storage, importer, jellyfin, sources, unrelated = _prepare(tmp_path)
    options = importer.selection_options(sources[0].name)
    assert len(options.choices) == 2
    assert {item.source_path for item in options.choices[0].sources} == {
        source.name for source in sources
    }
    html = Renderer(storage, config.output_path, config.timezone, True).render_selection(options)
    assert "2 Quellen für diesen Import" in html
    assert "2 Quellen für Eine Billion Dollar (2023) importieren" in html
    assert "S01E01" in html and "S01E02" in html
    assert all(source.name in html for source in sources)
    assert unrelated.name not in html
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


@pytest.mark.parametrize("phase", ["confirmation", "run"])
@pytest.mark.parametrize("change", ["added", "removed", "modified"])
def test_changed_preview_scope_blocks_before_any_move(tmp_path, phase, change) -> None:
    config, _, importer, jellyfin, sources, _ = _prepare(tmp_path)
    options = importer.selection_options(sources[0].name)
    selected = None
    if phase == "run":
        selected = importer.select_series(
            options.source_path, options.signature, options.choices[0].key
        )
    retained = sources[:]
    if change == "added":
        retained.append(release_folder(config.income_dir, "Eine.Billion.Dollar.S01E03.German"))
    elif change == "removed":
        retained[1] = sources[1].rename(tmp_path / "retained-source")
    else:
        next(sources[1].glob("*.mkv")).write_bytes(b"changed second source")

    with pytest.raises(SelectionUnavailable, match="Importumfang"):
        if phase == "confirmation":
            importer.select_series(options.source_path, options.signature, options.choices[0].key)
        else:
            importer.run(Library([]), force=True, selection=selected)

    assert all(source.exists() for source in retained)
    assert not list(config.shows_dir.iterdir())
    assert jellyfin.refresh_calls == 0


def test_unrelated_new_source_does_not_change_confirmed_scope(tmp_path) -> None:
    config, _, importer, _, sources, unrelated = _prepare(tmp_path)
    options = importer.selection_options(sources[0].name)
    other = release_folder(config.income_dir, "Another.Show.S01E01.German")
    selected = importer.select_series(options.source_path, options.signature, options.choices[0].key)
    assert importer.run(Library([]), force=True, selection=selected).transferred == 2
    assert all(not source.exists() for source in sources)
    assert other.exists() and unrelated.exists()


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
        start_selected_import(source_path, signature, choice_key)

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


@pytest.mark.parametrize("prepare", [_prepare, _prepare_title_mismatch])
def test_selection_page_endpoints_and_schedule(tmp_path, prepare) -> None:
    config, storage, importer, jellyfin, sources, _ = prepare(tmp_path)
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
        for remote in jellyfin.remote:
            for _, value in remote.provider_ids:
                assert value in page
        assert "https://www.imdb.com/title/" in page
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
        if options.choices[0].existing_series is not None:
            series = jellyfin.library.series[0]
            old_target = config.shows_dir / Path(series.path).name
            old_target.rename(config.shows_dir / "Current API path")
            jellyfin.library.series = [replace(series, path="/media/tv/Current API path")]
        assert request("POST", "/run/import/resolve", body, headers)[:2] == (303, "/#media-import")
        deadline = time.monotonic() + 3
        while scanner._lock.locked() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not scanner._lock.locked()
        assert storage.state()["manual_import_status"] == "ok"
        assert not sources[0].exists() and not sources[1].exists()
        if options.choices[0].existing_series is not None:
            assert all(
                (config.shows_dir / "Current API path" / "Staffel 02" / item.name).is_dir()
                for item in sources
            )
        assert storage.state()["next_run_at"] == next_run.isoformat()
        scanner.config = replace(config, media_import_enabled=False)
        assert request("GET", "/media-import/resolve?source=" + quote(source))[0] == 404
        assert request("POST", "/run/import/resolve", body, headers)[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
