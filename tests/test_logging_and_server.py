from __future__ import annotations

import http.client
import logging
import threading

from newtvshowsng2 import logging_utils
from newtvshowsng2.logging_utils import configure_logging, read_recent_log_lines
from newtvshowsng2.rendering import LogRenderer
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
