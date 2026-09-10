from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, PackageLoader, select_autoescape

from .logging_utils import LOG_PAGE_LINES, read_recent_log_lines
from .storage import Storage


class Renderer:
    def __init__(self, storage: Storage, output_path: Path, timezone: str) -> None:
        self.storage = storage
        self.output_path = output_path
        self.favicon_path = output_path.with_name("favicon.svg")
        self.timezone = ZoneInfo(timezone)
        self.environment = Environment(
            loader=PackageLoader("newtvshowsng2", "templates"),
            autoescape=select_autoescape(("html", "xml")),
        )
        self.environment.filters["local_datetime"] = self._local_datetime

    def render(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        current = self.storage.announcements(current_only=True)
        history = self.storage.announcements()
        state = self.storage.state()

        html = self.environment.get_template("index.html").render(
            current=current,
            history=history,
            state=state,
            generated_at=datetime.now(UTC),
        )
        self._atomic_write(self.output_path, html)
        favicon = (
            files("newtvshowsng2")
            .joinpath("static/favicon.svg")
            .read_text(encoding="utf-8")
        )
        self._atomic_write(self.favicon_path, favicon)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{path.stem}-", suffix=path.suffix, dir=path.parent, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, path)
        except BaseException:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def _local_datetime(self, value: str | datetime | None) -> str:
        if not value:
            return "–"
        try:
            parsed = (
                value if isinstance(value, datetime) else datetime.fromisoformat(value)
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(self.timezone).strftime("%d.%m.%Y, %H:%M")
        except (TypeError, ValueError):
            return str(value)


class LogRenderer:
    def __init__(self, log_path: Path, timezone: str) -> None:
        self.log_path = log_path
        self.timezone = ZoneInfo(timezone)
        self.environment = Environment(
            loader=PackageLoader("newtvshowsng2", "templates"),
            autoescape=select_autoescape(("html", "xml")),
        )

    def render(self) -> str:
        lines = read_recent_log_lines(self.log_path)
        return self.environment.get_template("log.html").render(
            log_text="\n".join(lines),
            line_count=len(lines),
            line_limit=LOG_PAGE_LINES,
            generated_at=datetime.now(UTC)
            .astimezone(self.timezone)
            .strftime("%d.%m.%Y, %H:%M:%S"),
        )
