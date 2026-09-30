from dataclasses import replace
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path

import pytest

from newtvshowsng2.config import Config
from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.media_importer import MediaImporter
import newtvshowsng2.media_importer as media_importer_module
from newtvshowsng2.models import Library, RemoteSeries, Series
from newtvshowsng2.storage import Storage


class Jellyfin:
    def __init__(self, remote=(), refresh_error=None):
        self.remote = list(remote)
        self.refresh_error = refresh_error
        self.refresh_calls = 0
        self.search_calls = []

    def tv_library_locations(self):
        return ("/media/tv",)

    def search_series(self, name, year=None, imdb_id=None):
        self.search_calls.append((name, year, imdb_id))
        return self.remote

    def refresh_library(self):
        self.refresh_calls += 1
        if self.refresh_error:
            raise self.refresh_error


def setup(tmp_path: Path, jellyfin: Jellyfin):
    income = tmp_path / "income"
    shows = tmp_path / "shows"
    income.mkdir()
    shows.mkdir()
    config = Config(
        jellyfin_url="http://jellyfin.test",
        jellyfin_api_key="secret",
        jellyfin_username="Hans",
        rss_urls=("https://feed.test/rss",),
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "out",
        income_dir=income,
        shows_dir=shows,
        jellyfin_shows_path="/media/tv",
        import_stable_hours=1,
        media_import_enabled=True,
    )
    storage = Storage(config.database_path)
    storage.initialize()
    return config, storage, MediaImporter(config, storage, jellyfin)


def release_folder(income: Path, name: str, video_name: str | None = None) -> Path:
    folder = income / name
    folder.mkdir()
    (folder / (video_name or f"{name}.mkv")).write_bytes(b"episode")
    return folder


def test_block_reason_is_logged_only_when_it_changes(tmp_path, caplog) -> None:
    _, storage, importer = setup(tmp_path, Jellyfin())
    storage.observe_media_import("Problem.S01E01.mkv", "signature", datetime(2026, 9, 30, tzinfo=UTC))

    with caplog.at_level(logging.WARNING):
        importer._record_block("Problem.S01E01.mkv", "Episode schon vorhanden")
        importer._record_block("Problem.S01E01.mkv", "Episode schon vorhanden")
        importer._record_block("Problem.S01E01.mkv", "Datei unvollständig")

    assert caplog.text.count("Problem.S01E01.mkv blockiert") == 2
    assert "Episode schon vorhanden" in caplog.text
    assert "Datei unvollständig" in caplog.text


def test_existing_series_release_folder_moves_after_stability_window(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series_folder = config.shows_dir / "Bookie (2023)"
    series_folder.mkdir()
    source = release_folder(
        config.income_dir, "Bookie.S02E09.German.DL.1080p.WEB.x264-WvF"
    )
    sample = source / "Sample"
    sample.mkdir()
    (sample / "bookie.s02e09.sample.mkv").write_bytes(b"sample")
    library = Library(
        [Series("bookie", "Bookie", production_year=2023, path="/media/tv/Bookie (2023)")]
    )
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    first = importer.run(library, started)
    second = importer.run(library, started + timedelta(hours=1))

    assert first.waiting == 1
    assert second.transferred == 1
    assert not source.exists()
    target = (
        series_folder
        / "Staffel 02"
        / "Bookie.S02E09.German.DL.1080p.WEB.x264-WvF"
    )
    assert (target / "Bookie.S02E09.German.DL.1080p.WEB.x264-WvF.mkv").is_file()
    assert (target / "Sample" / "bookie.s02e09.sample.mkv").is_file()
    assert not (target / ".ignore").exists()
    assert jellyfin.refresh_calls == 1
    row = storage.media_imports()[0]
    assert row["status"] == "transferred"
    assert row["target_path"].startswith("Bookie (2023)/Staffel 02/")


def test_income_observation_records_changes_without_importing(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    source = config.income_dir / "Bookie.S02E09.mkv"
    source.write_bytes(b"partial")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    assert importer.observe(started)
    row = storage.media_imports()[0]
    assert row["source_path"] == source.name
    assert row["status"] == "waiting"
    assert row["reason"] == "Wartet auf Importprüfung"
    assert row["first_seen_at"] == started.isoformat()
    assert not importer.observe(started + timedelta(seconds=15))
    assert storage.media_imports()[0]["first_seen_at"] == started.isoformat()
    storage.update_media_import(source.name, "blocked", "Prüfung fehlgeschlagen")
    assert not importer.observe(started + timedelta(seconds=30))
    assert storage.media_imports()[0]["status"] == "blocked"
    assert jellyfin.refresh_calls == 0
    assert not list(config.shows_dir.iterdir())

    source.write_bytes(b"complete")
    changed_at = started + timedelta(minutes=1)
    assert importer.observe(changed_at)
    assert storage.media_imports()[0]["first_seen_at"] == changed_at.isoformat()
    assert storage.media_imports()[0]["status"] == "waiting"

    source.unlink()
    assert importer.observe(changed_at + timedelta(seconds=15))
    assert storage.media_imports() == []


def test_income_work_check_includes_pending_jellyfin_refresh(tmp_path) -> None:
    config, storage, importer = setup(tmp_path, Jellyfin())
    assert not importer.has_work()
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"episode")
    assert importer.has_work()
    source.unlink()
    storage.set_library_refresh_pending(True)
    assert importer.has_work()


def test_forced_import_skips_stability_window_but_checks_source_changes(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series_folder = config.shows_dir / "Bookie (2023)"
    series_folder.mkdir()
    source = config.income_dir / "Bookie.S02E09.German.mkv"
    source.write_bytes(b"first")
    library = Library(
        [Series("bookie", "Bookie", production_year=2023, path="/media/tv/Bookie (2023)")]
    )
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    assert importer.run(library, started).waiting == 1
    source.write_bytes(b"changed")
    result = importer.run(library, started + timedelta(minutes=1), force=True)

    assert result.transferred == 1
    assert result.waiting == 0
    assert not source.exists()
    assert (series_folder / "Staffel 02" / source.name).read_bytes() == b"changed"
    assert storage.media_imports()[0]["status"] == "transferred"


def test_new_series_requires_one_exact_provider_match(tmp_path) -> None:
    remote = RemoteSeries("New Show", 2026, (("Imdb", "tt1234567"),))
    jellyfin = Jellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    source = release_folder(config.income_dir, "New.Show.2026.S01E01.German")
    library = Library([])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    target = (
        config.shows_dir
        / "New Show (2026) [imdbid-tt1234567]"
        / "Staffel 01"
        / source.name
    )
    assert result.transferred == 1
    assert target.is_dir()
    assert jellyfin.search_calls == [("New Show", 2026, None)]
    assert storage.media_imports()[0]["status"] == "transferred"


def test_new_series_accepts_unique_translated_title_with_matching_year(tmp_path) -> None:
    remote = RemoteSeries("Deutscher Titel", 2026, (("Tmdb", "456"),))
    jellyfin = Jellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    release_folder(config.income_dir, "English.Title.2026.S01E01.German")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(Library([]), started)
    result = importer.run(Library([]), started + timedelta(hours=1))

    assert result.transferred == 1
    assert (
        config.shows_dir
        / "Deutscher Titel (2026) [tmdbid-456]"
        / "Staffel 01"
    ).is_dir()
    assert storage.media_imports()[0]["status"] == "transferred"


def test_multiple_episodes_of_one_new_series_move_in_same_run(tmp_path) -> None:
    remote = RemoteSeries("New Show", 2026, (("Imdb", "tt1234567"),))
    jellyfin = Jellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    first = release_folder(config.income_dir, "New.Show.2026.S01E01.German")
    second = release_folder(config.income_dir, "New.Show.2026.S01E02.German")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(Library([]), started)
    result = importer.run(Library([]), started + timedelta(hours=1))

    season = (
        config.shows_dir
        / "New Show (2026) [imdbid-tt1234567]"
        / "Staffel 01"
    )
    assert result.transferred == 2
    assert (season / first.name).is_dir()
    assert (season / second.name).is_dir()
    assert jellyfin.search_calls == [("New Show", 2026, None)]
    assert jellyfin.refresh_calls == 1
    assert {row["status"] for row in storage.media_imports()} == {"transferred"}


def test_duplicate_episode_remains_in_income(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series_folder = config.shows_dir / "Bookie (2023)"
    series_folder.mkdir()
    source = release_folder(config.income_dir, "Bookie.S02E09.German")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie (2023)")])
    library.add_episode("bookie", 2, 9)
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "bereits vorhanden" in storage.media_imports()[0]["reason"]
    assert jellyfin.refresh_calls == 0


def test_ambiguous_new_series_and_multi_video_release_are_blocked(tmp_path) -> None:
    remotes = [
        RemoteSeries("New Show", 2026, (("Tvdb", "1"),)),
        RemoteSeries("New Show", 2026, (("Tvdb", "2"),)),
    ]
    jellyfin = Jellyfin(remotes)
    config, storage, importer = setup(tmp_path, jellyfin)
    ambiguous = release_folder(config.income_dir, "New.Show.2026.S01E01.German")
    multi = release_folder(config.income_dir, "Other.Show.S01E01.German")
    (multi / "Other.Show.S01E02.mkv").write_bytes(b"second")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(Library([]), started)
    result = importer.run(Library([]), started + timedelta(hours=1))

    assert result.blocked == 2
    assert ambiguous.exists() and multi.exists()
    reasons = {row["source_path"]: row["reason"] for row in storage.media_imports()}
    assert "nicht eindeutig" in reasons[ambiguous.name]
    assert "mehrere Hauptvideos" in reasons[multi.name]


def test_change_restarts_wait_and_failed_refresh_blocks_next_batch(tmp_path) -> None:
    jellyfin = Jellyfin(refresh_error=JellyfinError("offline"))
    config, storage, importer = setup(tmp_path, jellyfin)
    series_folder = config.shows_dir / "Bookie"
    series_folder.mkdir()
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"one")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    source.write_bytes(b"changed")
    changed = importer.run(library, started + timedelta(hours=1))
    transferred = importer.run(library, started + timedelta(hours=2))

    assert changed.waiting == 1
    assert transferred.transferred == 1
    assert transferred.warnings
    assert storage.library_refresh_pending()

    another = config.income_dir / "Bookie.S01E02.mkv"
    another.write_bytes(b"two")
    paused = importer.run(library, started + timedelta(hours=3))
    assert paused.transferred == 0
    assert paused.warnings
    assert another.exists()


def test_conflicting_folder_and_video_episode_is_blocked(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    (config.shows_dir / "Bookie").mkdir()
    source = release_folder(
        config.income_dir,
        "Bookie.S01E01.German",
        "Bookie.S01E02.German.mkv",
    )
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "widersprüchliche" in storage.media_imports()[0]["reason"]


def test_conflicting_folder_and_video_series_is_blocked(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    (config.shows_dir / "Bookie").mkdir()
    source = release_folder(
        config.income_dir,
        "Bookie.S01E01.German",
        "Different.Show.S01E01.German.mkv",
    )
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "widersprüchliche Serienangaben" in storage.media_imports()[0]["reason"]


@pytest.mark.parametrize(
    "release_name",
    [
        "Bookie.S01E01E02.German",
        "Bookie.S01E01-E02.German",
        "Bookie.S01E01-02.German",
        "Bookie.S01E01+E02.German",
    ],
)
def test_multi_episode_release_is_blocked(tmp_path, release_name) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    (config.shows_dir / "Bookie").mkdir()
    source = release_folder(config.income_dir, release_name)
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "Mehrteilige" in storage.media_imports()[0]["reason"]


def test_existing_alternative_season_folder_is_reused(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, _, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    existing_season = series / "Season 1"
    existing_season.mkdir(parents=True)
    source = release_folder(config.income_dir, "Bookie.S01E01.German")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.transferred == 1
    assert (existing_season / source.name).is_dir()
    assert not (series / "Staffel 01").exists()


def test_duplicate_is_found_from_parent_release_folder(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    existing = series / "Staffel 01" / "Bookie.S01E01.Release"
    existing.mkdir(parents=True)
    (existing / "episode.mkv").write_bytes(b"already here")
    source = release_folder(config.income_dir, "Bookie.S01E01.Other")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "bereits vorhanden" in storage.media_imports()[0]["reason"]


def test_unindexed_existing_series_folder_blocks_new_folder(tmp_path) -> None:
    remote = RemoteSeries("New Show", 2026, (("Imdb", "tt1234567"),))
    jellyfin = Jellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    (config.shows_dir / "New Show").mkdir()
    source = release_folder(config.income_dir, "New.Show.2026.S01E01.German")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(Library([]), started)
    result = importer.run(Library([]), started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "Möglicherweise vorhandener" in storage.media_imports()[0]["reason"]


def test_exact_empty_provider_folder_can_be_reused_after_interruption(tmp_path) -> None:
    remote = RemoteSeries("New Show", 2026, (("Imdb", "tt1234567"),))
    jellyfin = Jellyfin([remote])
    config, _, importer = setup(tmp_path, jellyfin)
    target_series = config.shows_dir / "New Show (2026) [imdbid-tt1234567]"
    (target_series / "Staffel 01").mkdir(parents=True)
    source = release_folder(config.income_dir, "New.Show.2026.S01E01.German")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(Library([]), started)
    result = importer.run(Library([]), started + timedelta(hours=1))

    assert result.transferred == 1
    assert (target_series / "Staffel 01" / source.name).is_dir()


def test_remote_provider_id_can_resolve_translated_existing_series(tmp_path) -> None:
    remote = RemoteSeries("English Name", 2026, (("Tmdb", "456"),))
    jellyfin = Jellyfin([remote])
    config, _, importer = setup(tmp_path, jellyfin)
    series_path = config.shows_dir / "Deutscher Name (2026)"
    series_path.mkdir()
    source = release_folder(config.income_dir, "English.Name.2026.S01E01.German")
    library = Library(
        [
            Series(
                "show",
                "Deutscher Name",
                production_year=2026,
                path="/media/tv/Deutscher Name (2026)",
                provider_ids=(("Tmdb", "456"),),
            )
        ]
    )
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.transferred == 1
    assert (series_path / "Staffel 01" / source.name).is_dir()
    assert not (config.shows_dir / "English Name (2026) [tmdbid-456]").exists()


def test_provider_resolved_existing_episode_is_blocked_by_jellyfin(tmp_path) -> None:
    remote = RemoteSeries("English Name", 2026, (("Tmdb", "456"),))
    jellyfin = Jellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    series_path = config.shows_dir / "Deutscher Name (2026)"
    series_path.mkdir()
    source = release_folder(config.income_dir, "English.Name.2026.S01E01.German")
    series = Series(
        "existing",
        "Deutscher Name",
        production_year=2026,
        path="/media/tv/Deutscher Name (2026)",
        provider_ids=(("Tmdb", "456"),),
    )
    library = Library([series])
    library.add_episode(series.id, 1, 1)
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert list(series_path.iterdir()) == []
    assert "laut Jellyfin bereits vorhanden" in storage.media_imports()[0]["reason"]


def test_conflicting_remote_provider_ids_block_existing_series(tmp_path) -> None:
    remote = RemoteSeries(
        "English Name", 2026, (("Tmdb", "456"), ("Imdb", "tt1111111"))
    )
    jellyfin = Jellyfin([remote])
    config, storage, importer = setup(tmp_path, jellyfin)
    series_path = config.shows_dir / "Deutscher Name (2026)"
    series_path.mkdir()
    source = release_folder(config.income_dir, "English.Name.2026.S01E01.German")
    library = Library(
        [
            Series(
                "existing",
                "Deutscher Name",
                production_year=2026,
                path="/media/tv/Deutscher Name (2026)",
                provider_ids=(("Tmdb", "456"), ("Imdb", "tt9999999")),
            )
        ]
    )
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert "widersprüchliche Provider-IDs" in storage.media_imports()[0]["reason"]


@pytest.mark.parametrize("force", [False, True])
def test_checksum_mismatch_keeps_source_and_creates_no_target(
    tmp_path, monkeypatch, force
) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    series.mkdir()
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"correct")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(library, started)

    def corrupt_copy(_source, destination, *args, **kwargs):
        Path(destination).write_bytes(b"xxxxxxx")

    monkeypatch.setattr(media_importer_module.shutil, "copy2", corrupt_copy)
    elapsed = timedelta(minutes=1) if force else timedelta(hours=1)
    result = importer.run(library, started + elapsed, force=force)

    assert result.blocked == 1
    assert source.read_bytes() == b"correct"
    assert not (series / "Staffel 01").exists()
    assert "Prüfsummenvergleich" in storage.media_imports()[0]["reason"]


def test_source_change_after_publish_keeps_both_copies_for_review(
    tmp_path, monkeypatch
) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    series.mkdir()
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"original")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(library, started)
    original_publish = media_importer_module._publish_without_overwrite

    def publish_then_change(stage, target):
        original_publish(stage, target)
        source.write_bytes(b"changed after publish")

    monkeypatch.setattr(
        media_importer_module, "_publish_without_overwrite", publish_then_change
    )
    result = importer.run(library, started + timedelta(hours=1))

    target = series / "Staffel 01" / source.name
    assert result.transferred == 1
    assert source.read_bytes() == b"changed after publish"
    assert target.read_bytes() == b"original"
    assert "manuellen Kontrolle" in storage.media_imports()[0]["reason"]
    assert jellyfin.refresh_calls == 1


def test_interruption_after_publication_preserves_pending_jellyfin_scan(
    tmp_path, monkeypatch
) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    series.mkdir()
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"episode")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(library, started)
    original_publish = media_importer_module._publish_without_overwrite

    def publish_then_interrupt(stage, target):
        original_publish(stage, target)
        raise KeyboardInterrupt

    monkeypatch.setattr(
        media_importer_module, "_publish_without_overwrite", publish_then_interrupt
    )
    with pytest.raises(KeyboardInterrupt):
        importer.run(library, started + timedelta(hours=1))

    assert source.exists()
    assert (series / "Staffel 01" / source.name).exists()
    assert storage.library_refresh_pending()

    monkeypatch.setattr(
        media_importer_module, "_publish_without_overwrite", original_publish
    )
    result = importer.run(library, started + timedelta(hours=2))

    assert jellyfin.refresh_calls == 1
    assert not storage.library_refresh_pending()
    assert result.blocked == 1


def test_publish_failure_keeps_source_and_does_not_delete_from_shows(
    tmp_path, monkeypatch
) -> None:
    remote = RemoteSeries("New Show", 2026, (("Imdb", "tt1234567"),))
    jellyfin = Jellyfin([remote])
    config, _, importer = setup(tmp_path, jellyfin)
    source = release_folder(config.income_dir, "New.Show.2026.S01E01.German")
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(Library([]), started)

    def fail_publish(_stage, _target):
        raise OSError("simulated publish failure")

    monkeypatch.setattr(
        media_importer_module, "_publish_without_overwrite", fail_publish
    )
    result = importer.run(Library([]), started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    new_series = config.shows_dir / "New Show (2026) [imdbid-tt1234567]"
    assert (new_series / "Staffel 01").is_dir()
    assert list((new_series / "Staffel 01").iterdir()) == []


def test_partial_directory_publication_is_left_untouched_for_review(
    tmp_path, monkeypatch
) -> None:
    jellyfin = Jellyfin()
    config, _, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    series.mkdir()
    source = release_folder(config.income_dir, "Bookie.S01E01.German")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(library, started)
    original_verify = media_importer_module._verify_copy
    calls = 0

    def fail_target_verification(source_path, destination, markers=frozenset()):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated target verification failure")
        return original_verify(source_path, destination, markers)

    monkeypatch.setattr(
        media_importer_module, "_verify_copy", fail_target_verification
    )
    result = importer.run(library, started + timedelta(hours=1))
    target = series / "Staffel 01" / source.name

    assert result.blocked == 1
    assert source.exists()
    assert target.is_dir()
    assert (target / ".ignore").exists()
    assert (target / ".newtvshowsng2-incomplete").exists()


def test_file_publication_error_does_not_remove_new_target(
    tmp_path, monkeypatch
) -> None:
    jellyfin = Jellyfin()
    config, _, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    series.mkdir()
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"episode")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(library, started)
    original_fsync = media_importer_module._fsync_directory

    def fail_target_parent(path):
        if path.name == "Staffel 01":
            raise OSError("simulated directory fsync failure")
        return original_fsync(path)

    monkeypatch.setattr(media_importer_module, "_fsync_directory", fail_target_parent)
    result = importer.run(library, started + timedelta(hours=1))
    target = series / "Staffel 01" / source.name

    assert result.blocked == 1
    assert source.exists()
    assert target.read_bytes() == b"episode"


def test_show_name_containing_sample_is_a_main_video(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, _, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Sampled Show"
    series.mkdir()
    source = release_folder(config.income_dir, "Sampled.Show.S01E01.German")
    library = Library(
        [Series("sampled", "Sampled Show", path="/media/tv/Sampled Show")]
    )
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.transferred == 1
    assert not source.exists()


def test_owned_incomplete_target_is_never_deleted_automatically(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    series = config.shows_dir / "Bookie"
    series.mkdir()
    source = release_folder(config.income_dir, "Bookie.S01E01.German")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    importer.run(library, started)

    incomplete = series / "Staffel 01" / source.name
    incomplete.mkdir(parents=True)
    (incomplete / ".ignore").touch()
    (incomplete / ".newtvshowsng2-incomplete").touch()
    (incomplete / "partial.mkv").write_bytes(b"partial")
    staging = config.shows_dir / ".newtvshowsng2-staging"
    staging.mkdir()
    (staging / ".ignore").touch()
    stale = staging / f"{'a' * 32}-old-release"
    stale.mkdir()
    (stale / "orphan.mkv").write_bytes(b"orphan")

    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert (stale / "orphan.mkv").read_bytes() == b"orphan"
    assert (incomplete / "partial.mkv").read_bytes() == b"partial"
    assert (incomplete / ".ignore").exists()
    assert (incomplete / ".newtvshowsng2-incomplete").exists()
    assert "manuell geprüft" in storage.media_imports()[0]["reason"]


def test_overlapping_income_and_shows_mounts_are_rejected(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, _ = setup(tmp_path, jellyfin)
    overlapping = replace(config, shows_dir=config.income_dir)
    importer = MediaImporter(overlapping, storage, jellyfin)

    with pytest.raises(JellyfinError, match="nicht überlappen"):
        importer.run(Library([]), datetime(2026, 9, 28, 10, tzinfo=UTC))


def test_symlinked_existing_series_cannot_escape_shows_root(tmp_path) -> None:
    jellyfin = Jellyfin()
    config, storage, importer = setup(tmp_path, jellyfin)
    outside = tmp_path / "outside"
    outside.mkdir()
    (config.shows_dir / "Bookie").symlink_to(outside, target_is_directory=True)
    source = config.income_dir / "Bookie.S01E01.mkv"
    source.write_bytes(b"episode")
    library = Library([Series("bookie", "Bookie", path="/media/tv/Bookie")])
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)

    importer.run(library, started)
    result = importer.run(library, started + timedelta(hours=1))

    assert result.blocked == 1
    assert source.exists()
    assert list(outside.iterdir()) == []
    assert "symbolischen Link" in storage.media_imports()[0]["reason"]


def test_source_is_reimported_if_previous_target_was_removed(
    tmp_path, monkeypatch
) -> None:
    jellyfin = Jellyfin()
    config, _, importer = setup(tmp_path, jellyfin)
    series_folder = config.shows_dir / "Bookie (2023)"
    series_folder.mkdir()
    source = config.income_dir / "Bookie.S02E09.German.mkv"
    source.write_bytes(b"episode")
    library = Library(
        [Series("bookie", "Bookie", production_year=2023, path="/media/tv/Bookie (2023)")]
    )
    started = datetime(2026, 9, 28, 10, tzinfo=UTC)
    original_unlink = Path.unlink

    def deny_source_unlink(path, *args, **kwargs):
        if path == source:
            raise PermissionError("test source remains")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", deny_source_unlink)
    importer.run(library, started)
    first = importer.run(library, started + timedelta(hours=1))
    target = series_folder / "Staffel 02" / source.name

    assert first.transferred == 1
    assert source.exists()
    assert target.exists()

    original_unlink(target)
    second = importer.run(library, started + timedelta(hours=2))

    assert second.transferred == 1
    assert source.exists()
    assert target.read_bytes() == b"episode"
