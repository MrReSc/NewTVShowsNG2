from __future__ import annotations

import http.client
import logging
import threading
from pathlib import Path
from urllib.parse import urlencode
from datetime import UTC, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from newtvshowsng2 import logging_utils
from newtvshowsng2.logging_utils import configure_logging, read_log_entries
from newtvshowsng2.rendering import LogRenderer, Renderer
from newtvshowsng2.server import ApplicationServer
from newtvshowsng2.storage import Storage
from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.media_importer import SelectionUnavailable


def test_configured_log_file_rotates(tmp_path, monkeypatch) -> None:
    assert logging_utils.LOG_MAX_BYTES == 2 * 1024 * 1024
    assert logging_utils.LOG_BACKUP_COUNT == 9
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    monkeypatch.setattr(logging_utils, "LOG_MAX_BYTES", 220)
    monkeypatch.setattr(logging_utils, "LOG_BACKUP_COUNT", 2)
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
        assert log_path.with_name("app.log.2").stat().st_size <= 220
        retained = "".join(
            path.read_text(encoding="utf-8")
            for path in (log_path.with_name("app.log.2"), log_path.with_name("app.log.1"), log_path)
        )
        assert "+00:00 INFO rotation-test:" in retained
        assert "Zeile 19" in retained
        assert "Zeile 00" not in retained
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_log_renderer_groups_tracebacks_and_escapes_content(tmp_path) -> None:
    log_path = tmp_path / "app.log"
    now = datetime(2026, 9, 30, 12, tzinfo=UTC)
    log_path.write_text(
        "2026-09-29 15:00:00,123 INFO newtvshowsng2.scanner: Alter Eintrag\n"
        "2026-09-30T11:00:00+00:00 ERROR newtvshowsng2.scanner: <script>alert(1)</script>\n"
        "Traceback (most recent call last):\n"
        "  File \"scan.py\", line 1, in run\n"
        "ValueError: kaputt\n",
        encoding="utf-8",
    )

    entries = read_log_entries(log_path, ZoneInfo("Europe/Zurich"))
    assert len(entries) == 2
    assert entries[0].timestamp == datetime(2026, 9, 29, 15, tzinfo=ZoneInfo("Europe/Zurich")).replace(microsecond=123000)
    assert "Traceback" in entries[1].details
    assert entries[0].raw_text == "2026-09-29 15:00:00,123 INFO newtvshowsng2.scanner: Alter Eintrag\n"
    assert entries[1].raw_text == (
        "2026-09-30T11:00:00+00:00 ERROR newtvshowsng2.scanner: <script>alert(1)</script>\n"
        "Traceback (most recent call last):\n"
        "  File \"scan.py\", line 1, in run\n"
        "ValueError: kaputt\n"
    )

    html = LogRenderer(log_path, "Europe/Zurich").render(now=now)

    assert "Alter Eintrag" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "Original anzeigen" not in html
    assert "Neueste Meldungen zuerst" not in html
    assert "Ältester gespeicherter Eintrag" not in html
    assert "<details" not in html
    assert html.count("&lt;script&gt;alert(1)&lt;/script&gt;") == 1
    assert 'class="button" href="/log/raw" target="_blank" rel="noopener noreferrer"' in html
    assert 'http-equiv="refresh"' not in html
    assert "Aktualisieren" in html
    assert '<a class="button reset" href="/log">Zurücksetzen</a>' in html
    assert html.index("&lt;script&gt;") < html.index("Alter Eintrag")
    assert "30.09.2026, 13:00:00 CEST" in html
    nav = html.split('<nav class="nav"', 1)[1].split("</nav>", 1)[0]
    assert (
        nav.index(">Feed</a>")
        < nav.index(">Medienimport</a>")
        < nav.index(">Historie</a>")
        < nav.index(">Log</a>")
    )


def test_log_originals_preserve_file_text_and_separate_rotation_boundaries(tmp_path) -> None:
    log_path = tmp_path / "app.log"
    archived = "2026-09-29T12:00:00Z INFO app: Rotierter Eintrag\n  Zusatz\n\n"
    prefix = "Unformatierter Beginn\r\n\t  Fortsetzung\r\n"
    current = (
        "2026-09-30 12:34:56,123 ERROR app: Grüsse <tag>\r\n"
        "\r\n\tTraceback mit Einrückung\r\n"
        "Letzte Zeile ohne Zeilenumbruch"
    )
    log_path.with_name("app.log.1").write_bytes(archived.encode("utf-8"))
    log_path.write_bytes((prefix + current).encode("utf-8"))

    entries = read_log_entries(log_path, ZoneInfo("Europe/Zurich"))

    assert [entry.raw_text for entry in entries] == [archived, prefix, current]
    assert entries[1].timestamp is None
    assert entries[2].details == "\n\tTraceback mit Einrückung\nLetzte Zeile ohne Zeilenumbruch"
    assert log_path.read_bytes() == (prefix + current).encode("utf-8")
    assert log_path.with_name("app.log.1").read_bytes() == archived.encode("utf-8")


def test_log_filters_search_and_pagination_include_all_backups(tmp_path, monkeypatch) -> None:
    now = datetime(2026, 9, 30, 12, tzinfo=UTC)
    log_path = tmp_path / "app.log"
    monkeypatch.setattr(logging_utils, "LOG_BACKUP_COUNT", 2)
    monkeypatch.setattr("newtvshowsng2.rendering.LOG_PAGE_ENTRIES", 2)
    log_path.with_name("app.log.2").write_text(
        "2026-09-23T11:59:59+00:00 ERROR app: too old\n"
        "2026-09-24T12:00:00+00:00 WARNING app: old warning\n", encoding="utf-8",
    )
    log_path.with_name("app.log.1").write_text(
        "2026-09-29T13:00:00+00:00 INFO app: recent info\n"
        "2026-09-30T09:00:00+00:00 WARNING app: recent warning\n", encoding="utf-8",
    )
    log_path.write_text(
        "2026-09-30T10:00:00+00:00 ERROR app: recent error\n", encoding="utf-8",
    )
    renderer = LogRenderer(log_path, "Europe/Zurich")

    default = renderer.render(now=now)
    assert "recent error" in default and "recent warning" in default
    assert "recent info" not in default
    assert "old warning" not in default
    assert 'href="/log?period=24h&amp;level=DEBUG&amp;page=2"' in default
    page_two = renderer.render("page=2", now=now)
    assert "recent info" in page_two and "recent error" not in page_two
    seven_days = renderer.render("period=7d&level=WARNING&page=2", now=now)
    assert "old warning" in seven_days and "too old" not in seven_days
    assert "Ältester gespeicherter Eintrag" not in seven_days
    searched = renderer.render("period=7d&level=WARNING&q=warning", now=now)
    assert "old warning" in searched and "recent warning" in searched
    assert "recent error" not in searched
    assert 'href="/log?period=7d&amp;level=WARNING&amp;q=warning&amp;page=1"' in searched


def test_server_serves_log_page(tmp_path) -> None:
    output_path = tmp_path / "index.html"
    output_path.write_text("<!doctype html><title>Übersicht</title>", encoding="utf-8")
    log_path = tmp_path / "app.log"
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    log_path.write_text(
        f"{stamp} INFO app: scan complete\n{stamp} ERROR app: scan failed\n",
        encoding="utf-8",
    )
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
        assert "form-action 'self'" in response.getheader("Content-Security-Policy")
        assert "font-src 'self'" in response.getheader("Content-Security-Policy")
        assert "script-src 'self'" in response.getheader("Content-Security-Policy")
        assert '<script src="/ui.js" defer></script>' in content
        assert "scan complete" in content
        connection.close()
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        connection.request("GET", "/log?level=ERROR")
        response = connection.getresponse()
        filtered = response.read().decode("utf-8")
        assert response.status == 200
        assert "scan failed" in filtered
        assert "scan complete" not in filtered
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_raw_log_returns_current_file_bytes_and_reports_read_errors(tmp_path, monkeypatch) -> None:
    output_path = tmp_path / "index.html"
    output_path.write_text("<!doctype html><title>Übersicht</title>", encoding="utf-8")
    log_path = tmp_path / "app.log"
    archived = b"2026-09-29T10:00:00Z INFO app: Nur im Archiv\n"
    log_path.with_name("app.log.1").write_bytes(archived)
    original = (
        "2026-09-30T10:00:00+00:00 INFO app: Grüsse\r\n"
        "\t<script>alert(1)</script>\r\n\r\n"
    ).encode("utf-8") + b"Unformatierte letzte Zeile \xff"
    log_path.write_bytes(original)
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    server = ApplicationServer(("127.0.0.1", 0), output_path, storage, log_path, "Europe/Zurich")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(*server.server_address, timeout=3)
    try:
        connection.request("GET", "/log/raw?period=7d&level=ERROR&path=../other.log")
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Type") == "text/plain; charset=utf-8"
        assert response.getheader("Content-Length") == str(len(original))
        assert response.getheader("Content-Disposition") == "inline"
        assert response.getheader("Cache-Control") == "no-store"
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert response.getheader("Referrer-Policy") == "no-referrer"
        assert "sandbox" in response.getheader("Content-Security-Policy")
        assert response.read() == original
        assert log_path.read_bytes() == original

        log_path.write_bytes(b"")
        connection.request("GET", "/log/raw")
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Length") == "0"
        assert response.read() == b""

        log_path.unlink()
        connection.request("GET", "/log/raw")
        response = connection.getresponse()
        html = response.read().decode("utf-8")
        assert response.status == 404
        assert "Die aktuelle Logdatei ist noch nicht vorhanden" in html
        assert 'href="/log">Zurück zum Log</a>' in html

        read_bytes = Path.read_bytes

        def unreadable(path):
            if path == log_path:
                raise PermissionError("Isolierter Lesefehler")
            return read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", unreadable)
        connection.request("GET", "/log/raw")
        response = connection.getresponse()
        html = response.read().decode("utf-8")
        assert response.status == 500
        assert "Die aktuelle Logdatei konnte nicht gelesen werden" in html
        assert 'href="/log">Zurück zum Log</a>' in html
        assert "Isolierter Lesefehler" not in html
        assert log_path.with_name("app.log.1").read_bytes() == archived
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_action_error_pages_escape_messages_and_keep_recovery_links(tmp_path) -> None:
    class Importer:
        def selection_options(self, source):
            raise SelectionUnavailable("Quelle <script>alert(1)</script> wurde verändert")

    class Scanner:
        config = SimpleNamespace(media_import_enabled=True)
        importer = Importer()

        def reopen_announcements(self, keys):
            raise JellyfinError("Jellyfin <script>alert(1)</script> ist nicht erreichbar")

    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    output = tmp_path / "index.html"
    output.write_text("<!doctype html><title>Übersicht</title>")
    server = ApplicationServer(
        ("127.0.0.1", 0), output, storage, tmp_path / "app.log", "Europe/Zurich", Scanner(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = "http://%s:%s" % server.server_address
        requests = [
            ("POST", "/announcements/reopen", urlencode({"source_key": "a" * 64}), 503, "/#history", "Zurück zur Historie"),
            ("GET", "/media-import/resolve?source=show", None, 409, "/#media-import", "Zurück zum Medienimport"),
        ]
        for method, path, body, status, return_url, label in requests:
            connection = http.client.HTTPConnection(*server.server_address, timeout=3)
            try:
                connection.request(method, path, body, {
                    "Origin": origin, "Content-Type": "application/x-www-form-urlencoded",
                })
                response = connection.getresponse()
                html = response.read().decode()
                assert response.status == status
                assert response.getheader("Cache-Control") == "no-store"
                assert "frame-ancestors 'none'" in response.getheader("Content-Security-Policy")
                assert "font-src 'self'" in response.getheader("Content-Security-Policy")
                assert "script-src 'self'" in response.getheader("Content-Security-Policy")
                assert '<script src="/ui.js" defer></script>' in html
                assert 'aria-label="Ansichten"' in html
                assert f'href="{return_url}">{label}</a>' in html
                assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
                assert "<script>alert(1)</script>" not in html
            finally:
                connection.close()
        connection = http.client.HTTPConnection(*server.server_address, timeout=3)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            assert "script-src 'self'" in response.getheader("Content-Security-Policy")
            assert "connect-src 'self'" in response.getheader("Content-Security-Policy")
            assert "font-src 'self'" in response.getheader("Content-Security-Policy")
            response.read()
            connection.request("GET", "/ui.js")
            response = connection.getresponse()
            assert response.status == 200
            assert response.getheader("Content-Type") == "text/javascript; charset=utf-8"
            assert b"data-run-feedback" in response.read()
            connection.request("GET", "/fonts/inter-4.1.woff2")
            response = connection.getresponse()
            font = response.read()
            assert response.status == 200
            assert response.getheader("Content-Type") == "font/woff2"
            assert response.getheader("Content-Length") == str(len(font))
            assert response.getheader("Cache-Control") == "public, max-age=31536000, immutable"
            assert response.getheader("X-Content-Type-Options") == "nosniff"
            assert font.startswith(b"wOF2")
            connection.request("GET", "/fonts/../server.py")
            response = connection.getresponse()
            assert response.status == 404
            response.read()
        finally:
            connection.close()
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
    assert 'method="post" action="/run/feed"' in html
    assert 'method="post" action="/run/import"' in html
    assert 'method="post" action="/run/income-scan"' in html
    media_view = html.split('id="media-import-view"', 1)[1].split('id="overview-view"', 1)[0]
    overview_view = html.split('id="overview-view"', 1)[1].split('id="history-view"', 1)[0]
    history_view = html.split('id="history-view"', 1)[1].split('<footer>', 1)[0]
    assert 'scan-state' not in html
    assert 'data-live-status' not in html
    assert 'class="count"' not in html
    assert "Nächster Lauf:" not in html
    assert 'action="/run/feed"' not in media_view
    assert 'action="/run/import"' not in overview_view
    assert 'action="/run/income-scan"' not in overview_view
    assert 'action="/run/feed"' not in history_view
    assert "(ohne Wartefrist)" not in html

    Renderer(storage, output, "Europe/Zurich", False).render()
    assert '<form method="post" action="/run/import"' not in output.read_text(encoding="utf-8")
    assert '<form method="post" action="/run/income-scan"' not in output.read_text(encoding="utf-8")


def test_manual_import_refreshes_only_while_running(tmp_path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    output = tmp_path / "index.html"
    renderer = Renderer(storage, output, "Europe/Zurich", True)
    started = datetime(2026, 9, 29, 10, tzinfo=UTC)

    storage.begin_manual_import(started)
    renderer.render()
    running = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in running
    assert 'src="/ui.js"' in running
    assert 'data-run-feedback="import" data-running="true"' in running
    assert "Manuelles Einsortieren läuft" in running
    assert 'data-run-start disabled' in running
    assert "Der Status wird im Hintergrund aktualisiert." in running
    assert "Ansicht aktualisieren" in running
    assert "Manuelles Einsortieren läuft" not in running.split('id="overview-view"', 1)[1]

    storage.complete_manual_import(started, "1 übernommen, 0 blockiert, 0 wartend", [])
    renderer.render()
    completed = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in completed
    assert "Manuelles Einsortieren abgeschlossen" not in completed
    assert 'data-run-feedback="import" data-running="false" hidden' in completed
    assert 'data-run-start disabled' not in completed

    storage.fail_manual_import(started, "Jellyfin nicht erreichbar")
    renderer.render()
    failed = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in failed
    assert "Manuelles Einsortieren fehlgeschlagen" not in failed
    assert 'data-run-feedback="import" data-running="false" hidden' in failed
    assert 'data-run-start disabled' not in failed


def test_manual_feed_refreshes_only_while_running(tmp_path) -> None:
    storage = Storage(tmp_path / "state.sqlite3")
    storage.initialize()
    output = tmp_path / "index.html"
    completed = datetime(2026, 9, 29, 10, tzinfo=UTC)
    storage.begin_scan(completed, None, manual=True)
    renderer = Renderer(storage, output, "Europe/Zurich")
    renderer.render()
    running = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in running
    assert 'data-run-feedback="feed" data-running="true"' in running
    assert "Feed-Abgleich läuft" in running
    assert "Feed-Abgleich läuft" not in running.split('id="media-import-view"', 1)[1].split('id="overview-view"', 1)[0]

    storage.complete_scan(completed, None, ["RSS-Abruf fehlgeschlagen"])
    renderer.render()

    html = output.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in html
    assert 'data-run-feedback="feed" data-running="false" hidden' in html
    assert "Feed-Abgleich abgeschlossen" not in html
    assert 'scan-state' not in html


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
        assert 'aria-label="Ansichten"' in body
        assert 'href="/#overview">Zurück zum Feed</a>' in body
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
