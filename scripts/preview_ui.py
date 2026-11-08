from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

from newtvshowsng2.rendering import Renderer

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/newtvshowsng2/static"
SELECTION_SOURCE = "Eine.Billion.Dollar.S01E01.German.1080p.mkv"
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class PreviewData:
    def __init__(self) -> None:
        self.now = datetime.now(UTC)
        self.renderer = Renderer(None, ROOT / "out/ui-preview/index.html", "Europe/Zurich")
        self.current = [
            self.release("MobLand", is_new=True),
            self.release("Tulsa King", season=4, jellyfin_episode_count=4,
                         jellyfin_expected_episode_count=10, needed_episodes=list(range(5, 11))),
            self.release("Eine Billion Dollar", match_warning=True),
            self.release("Eine aussergewöhnlich lange Serienbezeichnung mit ÄÖÜgjpq", episode=7),
        ]
        self.history = [
            self.release("Slow Horses", completed_at=self.now, is_current=False),
            *[
                self.release(name, is_current=False, status_reason=reason)
                for name, reason in (
                    ("The Bear", "available"), ("Severance", "played"),
                    ("Silo", "covered"), ("Dark Matter", "removed"),
                    ("The Last of Us", "unknown"),
                )
            ],
            dict(kind="import", source_path="MobLand.S02E01.German.1080p.mkv",
                 target_path="/media/Serien/MobLand/Staffel 02/MobLand.S02E01.mkv",
                 parsed_title="MobLand", season=2, episode=1, history_at=self.now),
        ]
        self.imports = [
            dict(source_path="Tulsa.King.S04E05.German.1080p.mkv", parsed_title="Tulsa King",
                 season=4, episode=5, status="waiting", target_path=None,
                 reason="Wartet auf die nächste Importprüfung"),
            dict(source_path="MobLand.S02E01.German.1080p.mkv", parsed_title="MobLand",
                 season=2, episode=1, status="blocked",
                 target_path="/media/Serien/MobLand/Staffel 02/MobLand.S02E01.mkv",
                 reason="Die Zieldatei ist bereits vorhanden"),
            dict(source_path=SELECTION_SOURCE, parsed_title="Eine Billion Dollar",
                 season=1, episode=1, status="needs_selection", target_path=None,
                 reason="Mehrere passende Serien gefunden. Wähle den gewünschten Treffer."),
        ]

    def release(self, name: str, **changes) -> dict:
        key = name.lower().replace(" ", "-")
        row = dict(
            kind="feed", matched_series_name=name, display_title=name, title=name,
            season=2, episode=None, published_at=self.now, history_at=self.now,
            source_key=key, source_keys=[key], completed_at=None,
            is_current=True, is_new=False, match_warning=False, needed_episodes=[],
            jellyfin_episode_count=0, jellyfin_expected_episode_count=None,
            link="/preview/release?" + urlencode({"title": name}),
            variants=[
                dict(link="/preview/release?" + urlencode({"title": name, "quality": quality}),
                     title=f"{name} German {quality}", label=quality)
                for quality in ("720p", "1080p", "2160p")
            ],
        )
        row.update(changes)
        return row

    def index(self, scenario: str = "") -> str:
        state = {"scan_status": "idle"}
        if scenario == "errors":
            state.update(
                last_error="Beispiel: Der Feed war vorübergehend nicht erreichbar.",
                automatic_import_error="Beispiel: Ein Import wurde wegen eines Zielkonflikts blockiert.",
                income_scan_error="Beispiel: Das Eingangsverzeichnis konnte nicht vollständig gelesen werden.",
                library_refresh_pending="1",
            )
        if scenario == "running":
            state.update(scan_status="running", manual_import_status="running")
        return self.renderer.environment.get_template("index.html").render(
            current=[] if scenario == "empty" else self.current,
            history=[] if scenario == "empty" else self.history,
            media_imports=[] if scenario == "empty" else self.imports,
            state=state, media_import_enabled=True, generated_at=self.now,
        )

    def selection(self, existing: bool = False) -> str:
        sources = tuple(
            SimpleNamespace(source_path=f"Eine.Billion.Dollar.S01E{episode:02d}.German.1080p.mkv",
                            season=1, episode=episode)
            for episode in (1, 2)
        )
        choices = tuple(
            SimpleNamespace(
                remote=SimpleNamespace(name="Eine Billion Dollar", production_year=year,
                                       provider_ids=(("Imdb", f"tt000000{index}"), ("Tmdb", str(index)))),
                existing_series=SimpleNamespace(name="Eine Billion Dollar", production_year=year) if existing else None,
                sources=sources, key=f"preview-{index}",
                imdb_url="/preview/release?provider=IMDb" if index == 1 else None,
            )
            for index, year in enumerate((2023, 2024), start=1)
        )
        return self.renderer.render_selection(SimpleNamespace(
            source_path=SELECTION_SOURCE, signature="local-preview",
            parsed=SimpleNamespace(series_title="Eine Billion Dollar"), choices=choices,
        ))

    def log(self, query: dict) -> str:
        level = query.get("level", ["DEBUG"])[0]
        if level not in LEVELS:
            level = "DEBUG"
        search = query.get("q", [""])[0]
        entries = []
        messages = (
            "Beispiel: Serienabgleich vorbereitet", "Beispiel: Feed-Abgleich abgeschlossen",
            "Beispiel: Serienzuordnung muss geprüft werden", "Beispiel: Zieldatei ist bereits vorhanden",
            "Beispiel: Eingangsverzeichnis vorübergehend nicht erreichbar",
        )
        for index in range(15):
            kind = index % len(LEVELS)
            stamp = self.now - timedelta(minutes=index)
            entry = dict(time=stamp.astimezone(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y, %H:%M:%S %Z"),
                         iso_time=stamp.isoformat(), level=LEVELS[kind], source="newtvshowsng2.preview",
                         message=messages[kind], raw_text=messages[kind])
            if kind >= LEVELS.index(level) and search.casefold() in entry["message"].casefold():
                entries.append(entry)
        try:
            requested = int(query.get("page", ["1"])[0])
        except ValueError:
            requested = 1
        page_count = max(1, (len(entries) + 4) // 5)
        page = max(1, min(requested, page_count))
        period = "7d" if query.get("period") == ["7d"] else "24h"

        def page_url(number: int) -> str:
            return "/log?" + urlencode(dict(period=period, level=level, q=search, page=number))

        return self.renderer.environment.get_template("log.html").render(
            entries=entries[(page - 1) * 5:page * 5], period=period, level=level,
            search=search, page=page, page_count=page_count, entry_count=len(entries),
            refresh_url=page_url(page), previous_url=page_url(page - 1) if page > 1 else None,
            next_url=page_url(page + 1) if page < page_count else None,
        )

    def catalogue(self) -> str:
        return self.renderer.environment.from_string("""<!doctype html>
<html lang="de-CH"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lokale Gestaltungsvorschau</title>{% include '_theme.html' %}
<style>.examples { display:flex; flex-wrap:wrap; gap:12px; padding:0; list-style:none; }</style>
</head><body><main class="shell">{% include '_navigation.html' %}
<h1>Lokale Gestaltungsvorschau</h1><p>Alle Ansichten verwenden Beispieldaten. Aktionen zeigen eine Rückmeldung ohne Verarbeitung.</p>
<ul class="examples">
{% for href, label in links %}<li><a class="button" href="{{ href }}">{{ label }}</a></li>{% endfor %}
</ul></main></body></html>""").render(links=(
            ("/#overview", "Feed mit Qualitätslinks und Statusvarianten"),
            ("/#media-import", "Import mit allen Statusvarianten"),
            ("/#history", "Historie mit Wiederöffnen und Import"),
            ("/log", "Log mit allen fünf Stufen"),
            ("/log?page=2", "Log mit beiden Seitenwechseln"),
            ("/media-import/resolve?source=" + SELECTION_SOURCE, "Serienzuordnung"),
            ("/media-import/resolve?existing=1", "Zuordnung einer vorhandenen Serie"),
            ("/?state=running#overview", "Laufender Feed-Abgleich"),
            ("/?state=running#media-import", "Laufender Import"),
            ("/?state=errors#overview", "Feed mit Fehlermeldung"),
            ("/?state=errors#media-import", "Import mit Warnungen und Fehlern"),
            ("/?state=empty#overview", "Leerer Feed"),
            ("/?state=empty#media-import", "Leerer Import"),
            ("/?state=empty#history", "Leere Historie"),
            ("/preview/error", "Fehlerseite"),
        ))


class PreviewHandler(BaseHTTPRequestHandler):
    def respond(self, content: str | bytes, mime: str = "text/html; charset=utf-8", status: int = 200) -> None:
        payload = content.encode("utf-8") if isinstance(content, str) else content
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; font-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        data = self.server.preview
        static = {
            "/ui.js": ("ui.js", "text/javascript; charset=utf-8"),
            "/fonts/inter-4.1.woff2": ("fonts/inter-4.1.woff2", "font/woff2"),
            "/favicon.svg": ("favicon.svg", "image/svg+xml"),
            "/series-placeholder.svg": ("series-placeholder.svg", "image/svg+xml"),
            "/series-image": ("series-placeholder.svg", "image/svg+xml"),
        }
        if url.path in static:
            name, mime = static[url.path]
            self.respond((STATIC / name).read_bytes(), mime)
        elif url.path in ("/", "/index.html", "/no-script"):
            html = data.index(query.get("state", [""])[0])
            if url.path == "/no-script":
                html = html.replace('<script src="/ui.js" defer></script>', '')
            self.respond(html)
        elif url.path in ("/log", "/log/"):
            self.respond(data.log(query))
        elif url.path == "/log/raw":
            self.respond("\n".join(f"{level} newtvshowsng2.preview: Beispiel für {level}" for level in LEVELS), "text/plain; charset=utf-8")
        elif url.path == "/media-import/resolve":
            self.respond(data.selection(query.get("existing") == ["1"]))
        elif url.path == "/preview":
            self.respond(data.catalogue())
        elif url.path == "/preview/release":
            self.respond(Renderer.render_error("Release-Beispiel", "Dieser Link gehört zur lokalen Gestaltungsvorschau.", "/#overview", "Zurück zum Feed"))
        else:
            self.respond(Renderer.render_error("Beispiel einer Fehlermeldung", "Die Zieldatei ist bereits vorhanden. Prüfe die Zuordnung vor einer erneuten Übernahme.", "/preview", "Zurück zu den Beispielansichten"), status=409 if url.path in ("/preview/error", "/preview-error") else 404)

    def do_POST(self) -> None:
        self.respond(Renderer.render_error("Lokale Gestaltungsvorschau", "Diese Aktion ist ein Gestaltungsbeispiel und verarbeitet keine Daten.", "/preview", "Zurück zu den Beispielansichten"), status=409)

    def log_message(self, *args) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Lokale UI-Vorschau mit isolierten Beispieldaten")
    parser.add_argument("--port", type=int, default=28733)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler) as server:
        server.preview = PreviewData()
        print(f"Lokale Vorschau: http://127.0.0.1:{args.port}/preview", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
