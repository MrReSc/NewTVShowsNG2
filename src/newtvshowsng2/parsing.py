from __future__ import annotations

import calendar
import html
import re
import unicodedata
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from .models import FeedRelease, ParsedRelease

RELEASE_MARKER = re.compile(
    r"(?<![A-Za-z0-9])S(?P<season>\d{1,3})(?:E(?P<episode>\d{1,3}))?(?!\d)",
    re.IGNORECASE,
)
IMDB_ID = re.compile(r"\btt\d{7,10}\b", re.IGNORECASE)
TRAILING_YEAR = re.compile(r"(?:^|\s)((?:19|20)\d{2})$")


def normalize_title(value: str) -> str:
    value = html.unescape(value).casefold()
    value = (
        value.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
        .replace("&", " and ")
        .replace("'", "")
        .replace("’", "")
    )
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def parse_release(title: str, content: str = "") -> ParsedRelease | None:
    marker = RELEASE_MARKER.search(title)
    if marker is None:
        return None

    series_title = re.sub(r"[.\s_-]+$", "", title[: marker.start()]).strip()
    normalized = normalize_title(series_title)
    if not normalized:
        return None

    year = None
    year_match = TRAILING_YEAR.search(normalized)
    if year_match:
        year = int(year_match.group(1))
        normalized = normalized[: year_match.start(1)].strip()

    imdb_match = IMDB_ID.search(content)
    return ParsedRelease(
        raw_title=title,
        series_title=series_title,
        normalized_title=normalized,
        year=year,
        season=int(marker.group("season")),
        episode=int(marker.group("episode")) if marker.group("episode") else None,
        imdb_id=imdb_match.group(0).lower() if imdb_match else None,
    )


def feed_entry_to_release(feed_url: str, entry: Any) -> FeedRelease | None:
    title = str(_entry_get(entry, "title", "")).strip()
    link = str(_entry_get(entry, "link", "")).strip()
    if not title or not _is_safe_http_url(link):
        return None

    guid_value = _entry_get(entry, "id", None) or _entry_get(entry, "guid", None)
    content_parts: list[str] = []
    content = _entry_get(entry, "content", []) or []
    for part in content:
        value = _entry_get(part, "value", "")
        if value:
            content_parts.append(str(value))
    summary = _entry_get(entry, "summary", "") or _entry_get(entry, "description", "")
    if summary:
        content_parts.append(str(summary))

    published_at = _entry_datetime(entry)
    return FeedRelease(
        feed_url=feed_url,
        guid=str(guid_value).strip() if guid_value else None,
        link=link,
        title=title,
        published_at=published_at,
        content="\n".join(content_parts),
    )


def _entry_datetime(entry: Any) -> datetime:
    for key in ("updated_parsed", "published_parsed"):
        parsed = _entry_get(entry, key, None)
        if parsed:
            return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)
    for key in ("updated", "published"):
        raw = _entry_get(entry, key, None)
        if raw:
            try:
                parsed = parsedate_to_datetime(str(raw))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed.astimezone(UTC)
            except (TypeError, ValueError, OverflowError):
                continue
    return datetime.now(UTC)


def _entry_get(entry: Any, key: str, default: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _is_safe_http_url(value: str) -> bool:
    return value.startswith(("https://", "http://"))
