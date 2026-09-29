from __future__ import annotations

import http.client
import logging
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

from newtvshowsng2 import logging_utils
from newtvshowsng2.logging_utils import configure_logging, read_recent_log_lines
from newtvshowsng2.rendering import LogRenderer, Renderer
from newtvshowsng2.server import ApplicationServer
from newtvshowsng2.storage import Storage


def test_recent_log_lines_include_backup_and_are_limited(tmp_path) -> None:
    log_path = tmp_path / "app.log"
    log_path.with_name("app.log.1").write_text("old-1\nold-2\n", encoding="utf-8")
    log_path.write_text("new-1\nnew-2\n", encoding="utf-8")

    assert read_recent_log_lines(log_path, limit=3) == ["old-2", "new-1", "new-2"]


def test_configured_log_file_rotates(tmp_path, monkeypatch) -> None:
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    monkeypatch.setattr(logging_utils, "LOG_MAX_BYTES", 220)
    log_path = tmp_path / "app.log"
    try:
        configure_logging(log_path, "INFO")
        for index in range(20):
            logging.getLogger("rotation-test").info("Zeile %02d %s", index, "x" * 40)
        for handler in root.handlers:
            handler.flush()
        assert log_path.exists()
        assert log_path.with_name("app.log.1").exists()
        assert log_path.stat().st_size <= 220
        assert log_path.with_name("app.log.1").stat().st_size <= 220
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_log_renderer_escapes_content_and_limits_lines(tmp_path) -> None:
    log_path = tmp_path / "app.log"
    lines = [f"line-{index}" for index in range(510)]
    lines[-1] = "<script>alert(1)</script>"
    log_path.write_text("\n".join(lines), encoding="utf-8")

    html = LogRenderer(log_path, "Europe/Zurich").render()

    assert "line-0" not in html
    assert "line-10" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert 'http-equiv="refresh" content="10"' in html


def test_server_serves_log_page(tmp_path) -> None:
    output_path = tmp_path / "index.html"
    output_path.write_text("<!doctype html><title>Übersicht</title>", encoding="utf-8")
    log_path = tmp_path / "app.log"
    log_path.write_text("scan complete", encoding="utf-8")
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    server = ApplicationServer(
        ("127.0.0.1", 0), output_path, storage, log_path, "Europe/Zurich"
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        connection.request("GET", "/log")
        response = connection.getresponse()
        content = response.read().decode("utf-8")
        assert response.status == 200
        assert response.getheader("Cache-Control") == "no-store"
        assert "scan complete" in content
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_manual_run_buttons_follow_import_setting(tmp_path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    output = tmp_path / "index.html"

    Renderer(storage, output, "Europe/Zurich", True).render()
    html = output.read_text(encoding="utf-8")
    header = html.split('<header class="topbar">', 1)[1].split('</header>', 1)[0]
    assert 'method="post" action="/run/feed"' in html
    assert 'method="post" action="/run/import"' in html
    assert 'method="post" action="/run/income-scan"' in html
    media_view = html.split('id="media-import-view"', 1)[1].split('id="overview-view"', 1)[0]
    overview_view = html.split('id="overview-view"', 1)[1].split('id="history-view"', 1)[0]
    history_view = html.split('id="history-view"', 1)[1].split('<footer>', 1)[0]
    assert 'scan-state' not in header
    assert "Nächster Lauf:" not in header
    assert 'action="/run/feed"' not in media_view
    assert 'action="/run/import"' not in overview_view
    assert 'action="/run/income-scan"' not in overview_view
    assert 'class="scan-state"' in media_view
    assert "Import bereit" in media_view
    assert 'class="scan-state starting"' in overview_view
    assert "Wird vorbereitet" in overview_view
    assert "Nächster Lauf:" in overview_view
    assert 'class="scan-state starting"' in history_view
    assert "Nächster Lauf:" in history_view
    assert 'action="/run/feed"' not in history_view
    assert "(ohne Wartefrist)" not in html

    Renderer(storage, output, "Europe/Zurich", False).render()
    assert 'action="/run/import"' not in output.read_text(encoding="utf-8")
    assert 'action="/run/income-scan"' not in output.read_text(encoding="utf-8")


def test_manual_import_refreshes_only_while_running(tmp_path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    output = tmp_path / "index.html"
    renderer = Renderer(storage, output, "Europe/Zurich", True)
    started = datetime(2026, 9, 29, 10, tzinfo=UTC)

    storage.begin_manual_import(started)
    renderer.render()
    running = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh" content="3"' in running
    assert "Manuelles Einsortieren läuft" in running
    assert 'class="scan-state running">Import läuft' in running
    assert "Die Seite wird nach dem Abschluss automatisch aktualisiert." in running
    assert "Manuelles Einsortieren läuft" not in running.split('id="overview-view"', 1)[1]

    storage.complete_manual_import(started, "1 übernommen, 0 blockiert, 0 wartend", [])
    renderer.render()
    completed = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in completed
    assert "Manuelles Einsortieren abgeschlossen" not in completed
    assert "Manuelles Einsortieren läuft" not in completed
    assert 'class="scan-state">Import bereit' in completed

    storage.fail_manual_import(started, "Jellyfin nicht erreichbar")
    renderer.render()
    failed = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in failed
    assert "Manuelles Einsortieren fehlgeschlagen" not in failed
    assert 'class="scan-state error">Letzter manueller Import fehlgeschlagen' in failed


def test_manual_feed_refreshes_only_while_running(tmp_path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    output = tmp_path / "index.html"
    completed = datetime(2026, 9, 29, 10, tzinfo=UTC)
    storage.begin_scan(completed, None, manual=True)
    renderer = Renderer(storage, output, "Europe/Zurich")
    renderer.render()
    running = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh" content="3"' in running
    assert "Feed-Abgleich läuft" in running
    assert "Feed-Abgleich läuft" not in running.split('id="media-import-view"', 1)[1].split('id="overview-view"', 1)[0]

    storage.complete_scan(completed, None, ["RSS-Abruf fehlgeschlagen"])
    renderer.render()

    html = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in html
    assert "Feed-Abgleich läuft" not in html
    assert "Feed-Abgleich abgeschlossen" not in html
    assert html.count('class="scan-state warning">') == 2


def test_error_notices_appear_only_in_matching_view(tmp_path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    completed = datetime(2026, 9, 29, 10, tzinfo=UTC)
    storage.fail_scan(completed, None, "Feed nicht erreichbar")
    storage.set_automatic_import_error("Import nicht möglich")
    storage.record_income_scan(completed, "Income nicht lesbar")
    storage.set_library_refresh_pending(True)
    output = tmp_path / "index.html"

    Renderer(storage, output, "Europe/Zurich", True).render()

    html = output.read_text(encoding="utf-8")
    media_view = html.split('id="media-import-view"', 1)[1].split('id="overview-view"', 1)[0]
    overview_view = html.split('id="overview-view"', 1)[1].split('id="history-view"', 1)[0]
    assert "Feed nicht erreichbar" in overview_view
    assert "Feed nicht erreichbar" not in media_view
    assert "Import nicht möglich" in media_view
    assert "Income nicht lesbar" in media_view
    assert "Jellyfin-Bibliotheksscan ausstehend" in media_view
    assert "Import nicht möglich" not in overview_view
    assert "Income nicht lesbar" not in overview_view


def test_manual_run_endpoints_accept_same_origin_and_reject_other_origins(tmp_path) -> None:
    class Scanner:
        importer = object()
        config = SimpleNamespace(media_import_enabled=True)

        def __init__(self):
            self.calls = []
            self.available = True

        def start_manual(self, kind):
            self.calls.append(kind)
            return self.available

        def scan_income(self):
            self.calls.append("income_scan")
            return False if self.available else None

    output_path = tmp_path / "index.html"
    output_path.write_text("<!doctype html><title>Übersicht</title>", encoding="utf-8")
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    scanner = Scanner()
    server = ApplicationServer(
        ("127.0.0.1", 0), output_path, storage, tmp_path / "app.log",
        "Europe/Zurich", scanner,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, headers=None):
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            status, location = response.status, response.getheader("Location")
            body = response.read().decode("utf-8")
            return status, location, body
        finally:
            connection.close()

    try:
        origin = f"http://127.0.0.1:{server.server_address[1]}"
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            assert response.status == 200
            assert response.getheader("Referrer-Policy") == "same-origin"
            response.read()
        finally:
            connection.close()
        assert request("POST", "/run/feed", {"Origin": origin})[:2] == (303, "/#overview")
        assert request("POST", "/run/import", {"Origin": origin})[:2] == (303, "/#media-import")
        assert request("POST", "/run/income-scan", {"Origin": origin})[:2] == (303, "/#media-import")
        assert request("POST", "/run/feed", {"Referer": origin + "/"})[0] == 303
        assert scanner.calls == ["feed", "import", "income_scan", "feed"]
        assert request("POST", "/run/feed", {"Origin": "http://foreign.test"})[0] == 403
        assert request("POST", "/run/feed", {"Sec-Fetch-Site": "cross-site"})[0] == 403
        assert request("POST", "/run/feed", {"Referer": "http://foreign.test/page"})[0] == 403
        assert request("POST", "/run/feed")[0] == 403
        assert request("POST", "/run/income-scan", {"Origin": "http://foreign.test"})[0] == 403
        assert scanner.calls == ["feed", "import", "income_scan", "feed"]
        scanner.available = False
        status, _, body = request("POST", "/run/feed", {"Origin": origin})
        assert status == 409
        assert "Ein anderer Lauf" in body
        assert request("POST", "/run/income-scan", {"Origin": origin})[0] == 409
        scanner.config.media_import_enabled = False
        assert request("POST", "/run/import", {"Origin": origin})[0] == 404
        assert request("POST", "/run/income-scan", {"Origin": origin})[0] == 404
        assert request("GET", "/run/feed")[0] == 404
        assert request("POST", "/run/unknown")[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
