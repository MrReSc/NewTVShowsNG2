from __future__ import annotations

import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment, PackageLoader, select_autoescape

from .logging_utils import LOG_PAGE_LINES, read_recent_log_lines
from .storage import Storage

QUALITY_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(2160[pi]|1080[pi]|720[pi]|576[pi]|480[pi]|4k|uhd)"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)
RELEASE_GROUP_PATTERN = re.compile(
    r"-\s*(?P<group>[A-Za-z0-9][A-Za-z0-9._]{0,31})\s*$"
)
QUALITY_DETAILS = {
    "480p": (480, "480p"),
    "480i": (480, "480i"),
    "576p": (576, "576p"),
    "576i": (576, "576i"),
    "720p": (720, "720p"),
    "720i": (720, "720i"),
    "1080p": (1080, "1080p"),
    "1080i": (1080, "1080i"),
    "2160p": (2160, "2160p"),
    "2160i": (2160, "2160i"),
    "4k": (2160, "4K"),
    "uhd": (2160, "UHD"),
}


class Renderer:
    def __init__(
        self, storage: Storage, output_path: Path, timezone: str,
        media_import_enabled: bool = False,
    ) -> None:
        self.storage = storage
        self.output_path = output_path
        self.favicon_path = output_path.with_name("favicon.svg")
        self.timezone = ZoneInfo(timezone)
        self.media_import_enabled = media_import_enabled
        self.environment = Environment(
            loader=PackageLoader("newtvshowsng2", "templates"),
            autoescape=select_autoescape(("html", "xml")),
        )
        self.environment.filters["local_datetime"] = self._local_datetime

    def render(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        current = group_current_releases(
            self.storage.announcements(current_only=True)
        )
        history = self.storage.announcements()
        media_imports = self.storage.media_imports()
        state = self.storage.state()
        html = self.environment.get_template("index.html").render(
            current=current,
            history=history,
            media_imports=media_imports,
            state=state,
            media_import_enabled=self.media_import_enabled,
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


def group_current_releases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, int, int | None], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["feed_url"]),
            str(row["matched_series_id"]),
            int(row["season"]),
            int(row["episode"]) if row["episode"] is not None else None,
        )
        buckets.setdefault(key, []).append(row)

    groups = [_build_release_group(group_rows) for group_rows in buckets.values()]
    return sorted(groups, key=_row_order, reverse=True)


def _build_release_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    newest = max(rows, key=_row_order)
    group = dict(newest)
    marker = f"S{int(newest['season']):02d}"
    if newest["episode"] is not None:
        marker += f"E{int(newest['episode']):02d}"
    base_title = newest["matched_series_name"]
    group["display_title"] = f"{base_title} · {marker}"
    group["is_new"] = any(bool(row["is_new"]) for row in rows)
    group["match_warning"] = any(bool(row["match_warning"]) for row in rows)
    group["variants"] = _release_variants(rows)
    return group


def _release_variants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants = []
    for row in rows:
        quality_rank, quality_label = _quality(str(row["title"]))
        variants.append(
            {
                "link": row["link"],
                "title": row["title"],
                "quality_rank": quality_rank,
                "base_label": quality_label,
                "release_group": _release_group(str(row["title"])),
                "published_at": row["published_at"],
            }
        )

    variants.sort(
        key=lambda item: (
            item["quality_rank"],
            item["base_label"].casefold(),
            item["published_at"],
            item["title"].casefold(),
        )
    )
    base_counts = Counter(item["base_label"] for item in variants)
    candidate_counts: Counter[str] = Counter()
    for item in variants:
        base_label = item["base_label"]
        if base_counts[base_label] == 1:
            candidate = base_label
        elif base_label == "Quelle":
            candidate = base_label
        elif item["release_group"]:
            candidate = f"{base_label} · {item['release_group']}"
        else:
            candidate = base_label
        item["candidate_label"] = candidate
        candidate_counts[candidate] += 1

    candidate_indexes: defaultdict[str, int] = defaultdict(int)
    source_index = 0
    for item in variants:
        candidate = item.pop("candidate_label")
        if item["base_label"] == "Quelle" and base_counts["Quelle"] > 1:
            source_index += 1
            item["label"] = f"Quelle {source_index}"
        elif candidate_counts[candidate] > 1:
            candidate_indexes[candidate] += 1
            item["label"] = f"{candidate} {candidate_indexes[candidate]}"
        else:
            item["label"] = candidate
    return variants


def _quality(title: str) -> tuple[int, str]:
    match = QUALITY_PATTERN.search(title)
    if match is None:
        return 10_000, "Quelle"
    return QUALITY_DETAILS[match.group(1).casefold()]


def _release_group(title: str) -> str | None:
    match = RELEASE_GROUP_PATTERN.search(title)
    return match.group("group") if match else None


def _row_order(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["published_at"]), str(row.get("first_seen_at", ""))


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
