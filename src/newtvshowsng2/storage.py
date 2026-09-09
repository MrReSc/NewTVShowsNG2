from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import FeedRelease, Library, Match, ParsedRelease

SCHEMA = """
CREATE TABLE IF NOT EXISTS announcements (
    source_key TEXT PRIMARY KEY,
    feed_url TEXT NOT NULL,
    guid TEXT,
    link TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    parsed_title TEXT NOT NULL,
    season INTEGER NOT NULL,
    episode INTEGER,
    imdb_id TEXT,
    matched_series_id TEXT NOT NULL,
    matched_series_name TEXT NOT NULL,
    match_method TEXT NOT NULL,
    match_warning INTEGER NOT NULL DEFAULT 0,
    jellyfin_episode INTEGER,
    is_current INTEGER NOT NULL DEFAULT 1,
    is_new INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS announcements_published
    ON announcements(published_at DESC);
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def begin_scan(self, started_at: datetime, next_run_at: datetime) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE announcements SET is_new = 0")
            self._set_many(
                connection,
                {
                    "scan_status": "running",
                    "scan_started_at": _iso(started_at),
                    "next_run_at": _iso(next_run_at),
                    "last_error": "",
                    "feed_errors": "[]",
                },
            )

    def complete_scan(
        self, completed_at: datetime, next_run_at: datetime, feed_errors: list[str]
    ) -> None:
        with self._connect() as connection:
            self._set_many(
                connection,
                {
                    "scan_status": "warning" if feed_errors else "ok",
                    "last_success_at": _iso(completed_at),
                    "last_scan_at": _iso(completed_at),
                    "next_run_at": _iso(next_run_at),
                    "last_error": "",
                    "feed_errors": json.dumps(feed_errors, ensure_ascii=False),
                },
            )

    def fail_scan(self, failed_at: datetime, next_run_at: datetime, error: str) -> None:
        with self._connect() as connection:
            self._set_many(
                connection,
                {
                    "scan_status": "error",
                    "last_scan_at": _iso(failed_at),
                    "next_run_at": _iso(next_run_at),
                    "last_error": error,
                },
            )

    def upsert_release(
        self,
        feed: FeedRelease,
        parsed: ParsedRelease,
        match: Match,
        library: Library,
        seen_at: datetime,
    ) -> None:
        source_key = _source_key(feed)
        content_hash = hashlib.sha256(
            f"{feed.title}\0{feed.link}\0{feed.published_at.isoformat()}\0{feed.content}".encode()
        ).hexdigest()
        local_episode = library.episode_in_season(match.series.id, parsed.season)
        is_current = (
            not library.episode_exists(match.series.id, parsed.season, parsed.episode)
            if parsed.episode is not None
            else library.season_is_current(match.series.id, parsed.season)
        )

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT content_hash FROM announcements WHERE source_key = ?",
                (source_key,),
            ).fetchone()
            is_new = existing is None or existing["content_hash"] != content_hash
            connection.execute(
                """
                INSERT INTO announcements (
                    source_key, feed_url, guid, link, title, published_at,
                    first_seen_at, last_seen_at, content_hash, parsed_title,
                    season, episode, imdb_id, matched_series_id,
                    matched_series_name, match_method, match_warning,
                    jellyfin_episode, is_current, is_new
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    guid = excluded.guid,
                    link = excluded.link,
                    title = excluded.title,
                    published_at = excluded.published_at,
                    last_seen_at = excluded.last_seen_at,
                    content_hash = excluded.content_hash,
                    parsed_title = excluded.parsed_title,
                    season = excluded.season,
                    episode = excluded.episode,
                    imdb_id = excluded.imdb_id,
                    matched_series_id = excluded.matched_series_id,
                    matched_series_name = excluded.matched_series_name,
                    match_method = excluded.match_method,
                    match_warning = excluded.match_warning,
                    jellyfin_episode = excluded.jellyfin_episode,
                    is_current = excluded.is_current,
                    is_new = excluded.is_new
                """,
                (
                    source_key,
                    feed.feed_url,
                    feed.guid,
                    feed.link,
                    feed.title,
                    _iso(feed.published_at),
                    _iso(seen_at),
                    _iso(seen_at),
                    content_hash,
                    parsed.series_title,
                    parsed.season,
                    parsed.episode,
                    parsed.imdb_id,
                    match.series.id,
                    match.series.name,
                    match.method,
                    int(match.warning),
                    local_episode,
                    int(is_current),
                    int(is_new),
                ),
            )

    def refresh_library_state(self, library: Library) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT source_key, matched_series_id, season, episode FROM announcements"
            ).fetchall()
            valid_ids = {series.id for series in library.series}
            for row in rows:
                series_id = row["matched_series_id"]
                season = row["season"]
                episode = row["episode"]
                if series_id not in valid_ids:
                    is_current = False
                    local_episode = None
                else:
                    local_episode = library.episode_in_season(series_id, season)
                    is_current = (
                        not library.episode_exists(series_id, season, episode)
                        if episode is not None
                        else library.season_is_current(series_id, season)
                    )
                connection.execute(
                    """
                    UPDATE announcements
                    SET jellyfin_episode = ?, is_current = ?
                    WHERE source_key = ?
                    """,
                    (local_episode, int(is_current), row["source_key"]),
                )

    def prune(self, max_history: int) -> None:
        with self._connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM announcements").fetchone()[
                0
            ]
            excess = max(0, count - max_history)
            if not excess:
                return
            connection.execute(
                """
                DELETE FROM announcements WHERE source_key IN (
                    SELECT source_key FROM announcements
                    ORDER BY is_current ASC, published_at ASC, first_seen_at ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )

    def announcements(self, current_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM announcements"
        if current_only:
            query += " WHERE is_current = 1"
        query += " ORDER BY published_at DESC, first_seen_at DESC"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query).fetchall()]

    def state(self) -> dict[str, str]:
        with self._connect() as connection:
            return {
                row["key"]: row["value"]
                for row in connection.execute("SELECT key, value FROM app_state")
            }

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _set_many(connection: sqlite3.Connection, values: dict[str, str]) -> None:
        connection.executemany(
            """
            INSERT INTO app_state(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            values.items(),
        )


def _source_key(feed: FeedRelease) -> str:
    identity = feed.guid or feed.link
    return hashlib.sha256(f"{feed.feed_url}\0{identity}".encode()).hexdigest()


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
