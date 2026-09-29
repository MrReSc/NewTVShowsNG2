from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event, Thread

from newtvshowsng2.media_importer import ImportRunResult, MediaImporter
from newtvshowsng2.models import Library
from newtvshowsng2.rendering import Renderer
from newtvshowsng2.scanner import Scanner
from test_scanner_and_rendering import Jellyfin, setup


class CountingFeeds:
    def __init__(self) -> None:
        self.calls = 0

    def load(self, _url):
        self.calls += 1
        return []


class CountingImporter:
    def __init__(self, result: ImportRunResult | None = None) -> None:
        self.calls: list[bool] = []
        self.result = result or ImportRunResult(transferred=2, blocked=1)
        self.work_available = True

    def has_work(self):
        return self.work_available

    def run(self, _library, _now, *, force: bool):
        self.calls.append(force)
        return self.result


def wait_for(predicate) -> None:
    deadline = time.monotonic() + 3
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("Lauf wurde nicht rechtzeitig abgeschlossen")
        time.sleep(0.01)


def test_manual_run_modes_are_separate_and_keep_automatic_schedule(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    cfg = replace(cfg, media_import_enabled=True)
    next_run = datetime(2026, 9, 30, 12, tzinfo=UTC)
    storage.begin_scan(next_run - timedelta(hours=1), next_run)
    storage.complete_scan(next_run - timedelta(hours=1), next_run, [])
    feeds = CountingFeeds()
    importer = CountingImporter()
    scanner = Scanner(cfg, storage, renderer, Jellyfin(Library([])), feeds, importer)

    assert scanner.start_manual("feed")
    wait_for(lambda: storage.state()["scan_status"] == "ok")
    wait_for(lambda: not scanner._lock.locked())
    assert feeds.calls == 1
    assert importer.calls == []
    assert storage.state()["next_run_at"] == next_run.isoformat()
    feed_state = {key: storage.state()[key] for key in ("scan_status", "last_success_at")}

    assert scanner.start_manual("import")
    wait_for(lambda: storage.state().get("manual_import_status") == "ok")
    wait_for(lambda: not scanner._lock.locked())
    assert importer.calls == [True]
    assert feeds.calls == 1
    assert storage.state()["next_run_at"] == next_run.isoformat()
    assert {key: storage.state()[key] for key in feed_state} == feed_state
    assert "2 übernommen, 1 blockiert" in cfg.output_path.read_text()


def test_automatic_run_waits_for_manual_run_and_uses_stability_window(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    cfg = replace(cfg, media_import_enabled=True)
    entered = Event()
    release = Event()

    class BlockingFeeds(CountingFeeds):
        def load(self, url):
            if self.calls == 0:
                entered.set()
                assert release.wait(timeout=3)
            return super().load(url)

    feeds = BlockingFeeds()
    importer = CountingImporter()
    scanner = Scanner(cfg, storage, renderer, Jellyfin(Library([])), feeds, importer)

    assert scanner.start_manual("feed")
    assert entered.wait(timeout=3)
    assert not scanner.start_manual("import")
    scheduled = Thread(target=scanner.run)
    scheduled.start()
    assert scheduled.is_alive()
    assert importer.calls == []

    release.set()
    scheduled.join(timeout=3)
    assert not scheduled.is_alive()
    assert feeds.calls == 2
    assert importer.calls == [False]


def test_manual_import_failure_does_not_change_feed_status(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    cfg = replace(cfg, media_import_enabled=True)
    next_run = datetime(2026, 9, 30, 12, tzinfo=UTC)
    storage.begin_scan(next_run - timedelta(hours=1), next_run)
    storage.complete_scan(next_run - timedelta(hours=1), next_run, [])
    jellyfin = Jellyfin(Library([]))

    def fail():
        raise RuntimeError("Jellyfin nicht erreichbar")

    jellyfin.load_library = fail
    scanner = Scanner(cfg, storage, renderer, jellyfin, CountingFeeds(), CountingImporter())
    assert scanner.start_manual("import")
    wait_for(lambda: storage.state().get("manual_import_status") == "error")
    assert storage.state()["scan_status"] == "ok"
    assert storage.state()["next_run_at"] == next_run.isoformat()
    assert "Jellyfin nicht erreichbar" in cfg.output_path.read_text()


def test_interrupted_manual_import_is_reported_after_restart(tmp_path) -> None:
    _, storage, _ = setup(tmp_path)
    storage.begin_manual_import(datetime(2026, 9, 29, 10, tzinfo=UTC))

    storage.recover_interrupted_manual_import()

    state = storage.state()
    assert state["manual_import_status"] == "error"
    assert "Neustart unterbrochen" in state["manual_import_error"]


def test_feed_and_hourly_import_are_independent(tmp_path) -> None:
    cfg, storage, renderer = setup(tmp_path)
    cfg = replace(cfg, media_import_enabled=True)
    feeds = CountingFeeds()
    importer = CountingImporter()
    scanner = Scanner(cfg, storage, renderer, Jellyfin(Library([])), feeds, importer)

    assert scanner.run_feed()
    next_feed_run = storage.state()["next_run_at"]
    assert feeds.calls == 1
    assert importer.calls == []

    importer.work_available = False
    assert not scanner.run_scheduled_import()
    assert importer.calls == []

    importer.work_available = True
    assert scanner.run_scheduled_import()
    assert importer.calls == [False]
    assert feeds.calls == 1
    assert storage.state()["next_run_at"] == next_feed_run
    assert storage.state()["scan_status"] == "ok"


def test_income_scan_updates_page_without_automatic_refresh(tmp_path) -> None:
    cfg, storage, _ = setup(tmp_path)
    income = tmp_path / "income"
    income.mkdir()
    cfg = replace(cfg, media_import_enabled=True, income_dir=income)
    renderer = Renderer(storage, cfg.output_path, cfg.timezone, True)
    jellyfin = Jellyfin(Library([]))

    def unexpected_jellyfin_call(*_args, **_kwargs):
        raise AssertionError("Income-Scan darf Jellyfin nicht abfragen")

    jellyfin.load_library = unexpected_jellyfin_call
    jellyfin.tv_library_locations = unexpected_jellyfin_call
    importer = MediaImporter(cfg, storage, jellyfin)
    feeds = CountingFeeds()
    scanner = Scanner(cfg, storage, renderer, jellyfin, feeds, importer)
    source = income / "Bookie.S02E09.mkv"
    source.write_bytes(b"still copying")

    assert scanner.scan_income()
    assert not scanner.scan_income()

    html = cfg.output_path.read_text(encoding="utf-8")
    assert source.name in html
    assert "Wartet auf Importprüfung" in html
    assert 'http-equiv="refresh"' not in html
    assert "Income gescannt" in html
    assert "Dateien jetzt einsortieren" in html
    assert "(ohne Wartefrist)" not in html
    assert source.exists()
    assert feeds.calls == 0
