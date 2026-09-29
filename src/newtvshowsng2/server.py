from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .rendering import LogRenderer
from .scanner import Scanner
from .storage import Storage

LOGGER = logging.getLogger(__name__)


class ApplicationServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        output_path: Path,
        storage: Storage,
        log_path: Path,
        timezone: str,
        scanner: Scanner | None = None,
    ):
        super().__init__(address, RequestHandler)
        self.output_path = output_path
        self.storage = storage
        self.log_renderer = LogRenderer(log_path, timezone)
        self.scanner = scanner


class RequestHandler(BaseHTTPRequestHandler):
    server: ApplicationServer

    def do_POST(self) -> None:
        if self.path not in ("/run/feed", "/run/import"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        scanner = self.server.scanner
        kind = "feed" if self.path == "/run/feed" else "import"
        if scanner is None or (
            kind == "import"
            and (not scanner.config.media_import_enabled or scanner.importer is None)
        ):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._same_origin_request():
            self.send_error(HTTPStatus.FORBIDDEN, "Fremder Ursprung ist nicht erlaubt")
            return
        try:
            started = scanner.start_manual(kind)
        except Exception:
            LOGGER.exception("Manueller %s-Lauf konnte nicht gestartet werden", kind)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Lauf konnte nicht gestartet werden")
            return
        if not started:
            self.send_error(HTTPStatus.CONFLICT, "Ein anderer Lauf ist bereits aktiv")
            return
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/#overview" if kind == "feed" else "/#media-import")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _same_origin_request(self) -> bool:
        fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        if fetch_site in ("cross-site", "same-site"):
            return False
        origin = self.headers.get("Origin")
        referer = self.headers.get("Referer")
        if origin is None and referer is None:
            return fetch_site == "same-origin"
        origin = origin or referer
        if origin is None:
            return False
        parsed = urlsplit(origin)
        return (
            parsed.scheme == "http"
            and parsed.netloc == self.headers.get("Host")
            and (not self.headers.get("Origin") or parsed.path == "")
        )

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._serve_index()
        elif path in ("/log", "/log/"):
            self._serve_log()
        elif path in ("/favicon.svg", "/favicon.ico"):
            self._serve_favicon()
        elif path == "/healthz":
            self._serve_health()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _serve_index(self) -> None:
        try:
            content = self.server.output_path.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Ausgabe wird vorbereitet")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(content)

    def _serve_log(self) -> None:
        try:
            content = self.server.log_renderer.render().encode("utf-8")
        except OSError:
            LOGGER.exception("Logseite konnte nicht erzeugt werden")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(content)

    def _serve_favicon(self) -> None:
        favicon_path = self.server.output_path.with_name("favicon.svg")
        try:
            content = favicon_path.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def _serve_health(self) -> None:
        state = self.server.storage.state()
        payload: dict[str, Any] = {
            "status": state.get("scan_status", "starting"),
            "last_success_at": state.get("last_success_at"),
            "last_error": state.get("last_error") or None,
        }
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.debug("HTTP %s - %s", self.address_string(), format % args)
