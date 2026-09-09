from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from jinja2 import Environment, PackageLoader, select_autoescape

from .storage import Storage


class Renderer:
    def __init__(self, storage: Storage, output_path: Path, timezone: str) -> None:
        self.storage = storage
        self.output_path = output_path
        self.timezone = ZoneInfo(timezone)
        self.environment = Environment(
            loader=PackageLoader("newtvshowsng2", "templates"),
            autoescape=select_autoescape(("html", "xml")),
        )
        self.environment.filters["local_datetime"] = self._local_datetime
        self.environment.filters["source_name"] = _source_name

    def render(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        current = self.storage.announcements(current_only=True)
        history = self.storage.announcements()
        state = self.storage.state()
        try:
            feed_errors = json.loads(state.get("feed_errors", "[]"))
        except json.JSONDecodeError:
            feed_errors = []

        html = self.environment.get_template("index.html").render(
            current=current,
            history=history,
            state=state,
            feed_errors=feed_errors,
            current_count=len(current),
            new_count=sum(bool(row["is_new"]) for row in history),
            generated_at=datetime.now(UTC),
        )
        self._atomic_write(html)

    def _atomic_write(self, content: str) -> None:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".index-", suffix=".html", dir=self.output_path.parent, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, self.output_path)
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


def _source_name(value: str) -> str:
    try:
        return urlsplit(value).netloc or "Quelle"
    except ValueError:
        return "Quelle"
