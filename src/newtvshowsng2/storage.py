from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from .models import FeedRelease, Library, Match, ParsedRelease
from .parsing import parse_release

SCHEMA = """
CREATE TABLE IF NOT EXISTS announcements (
    source_key TEXT PRIMARY KEY,
    feed_item_key TEXT NOT NULL,
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
    jellyfin_episode_count INTEGER,
    jellyfin_expected_episode_count INTEGER,
    jellyfin_played_episode_count INTEGER,
    needed_episodes TEXT,
    status_reason TEXT,
    is_current INTEGER NOT NULL DEFAULT 1,
    is_new INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS announcements_published
    ON announcements(published_at DESC);
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_imports (
    source_path TEXT PRIMARY KEY,
    signature TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    parsed_title TEXT,
    season INTEGER,
    episode INTEGER,
    target_path TEXT,
    transferred_at TEXT
);
CREATE INDEX IF NOT EXISTS media_imports_last_seen
    ON media_imports(last_seen_at DESC);
"""


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            self._ensure_column(
                connection, "announcements", "jellyfin_episode_count", "INTEGER"
            )
            self._ensure_column(
                connection,
                "announcements",
                "jellyfin_expected_episode_count",
                "INTEGER",
            )
            for column, definition in (
                ("jellyfin_played_episode_count", "INTEGER"),
                ("needed_episodes", "TEXT"),
                ("status_reason", "TEXT"),
            ):
                self._ensure_column(connection, "announcements", column, definition)
            self._ensure_column(
                connection, "announcements", "feed_item_key", "TEXT"
            )
            self._migrate_feed_item_keys(connection)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS announcements_feed_item "
                "ON announcements(feed_item_key)"
            )

    def begin_scan(
        self, started_at: datetime, next_run_at: datetime | None, *, manual: bool = False
    ) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE announcements SET is_new = 0")
            values = {
                "scan_status": "running",
                "scan_origin": "manual" if manual else "automatic",
                "scan_started_at": _iso(started_at),
                "last_error": "",
                "feed_errors": "[]",
            }
            if next_run_at is not None:
                values["next_run_at"] = _iso(next_run_at)
            self._set_many(connection, values)

    def complete_scan(
        self, completed_at: datetime, next_run_at: datetime | None, feed_errors: list[str]
    ) -> None:
        with self._connect() as connection:
            values = {
                "scan_status": "warning" if feed_errors else "ok",
                "last_success_at": _iso(completed_at),
                "last_scan_at": _iso(completed_at),
                "last_error": "",
                "feed_errors": json.dumps(feed_errors, ensure_ascii=False),
            }
            if next_run_at is not None:
                values["next_run_at"] = _iso(next_run_at)
            self._set_many(connection, values)

    def fail_scan(
        self, failed_at: datetime, next_run_at: datetime | None, error: str
    ) -> None:
        with self._connect() as connection:
            values = {
                "scan_status": "error",
                "last_scan_at": _iso(failed_at),
                "last_error": error,
            }
            if next_run_at is not None:
                values["next_run_at"] = _iso(next_run_at)
            self._set_many(connection, values)

    def begin_manual_import(self, started_at: datetime) -> None:
        with self._connect() as connection:
            self._set_many(
                connection,
                {
                    "manual_import_status": "running",
                    "manual_import_started_at": _iso(started_at),
                    "manual_import_error": "",
                    "manual_import_summary": "",
                },
            )

    def recover_interrupted_manual_import(self) -> None:
        with self._connect() as connection:
            status = connection.execute(
                "SELECT value FROM app_state WHERE key = 'manual_import_status'"
            ).fetchone()
            if status is not None and status["value"] == "running":
                self._set_many(
                    connection,
                    {
                        "manual_import_status": "error",
                        "manual_import_finished_at": _iso(datetime.now(UTC)),
                        "manual_import_error": (
                            "Der manuelle Import wurde durch einen Neustart unterbrochen; "
                            "Dateien und Jellyfin-Status bitte prüfen"
                        ),
                    },
                )

    def complete_manual_import(
        self, completed_at: datetime, summary: str, warnings: list[str]
    ) -> None:
        with self._connect() as connection:
            self._set_many(
                connection,
                {
                    "manual_import_status": "warning" if warnings else "ok",
                    "manual_import_finished_at": _iso(completed_at),
                    "manual_import_summary": summary,
                    "manual_import_error": "\n".join(warnings),
                },
            )

    def fail_manual_import(self, failed_at: datetime, error: str) -> None:
        with self._connect() as connection:
            self._set_many(
                connection,
                {
                    "manual_import_status": "error",
                    "manual_import_finished_at": _iso(failed_at),
                    "manual_import_error": error,
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
        feed_item_key = _feed_item_key(feed)
        content_hash = hashlib.sha256(
            f"{feed.title}\0{feed.link}\0{feed.published_at.isoformat()}\0{feed.content}".encode()
        ).hexdigest()
        source_keys = [
            _source_key(feed_item_key, season, parsed.episode)
            for season in parsed.seasons
        ]

        with self._connect() as connection:
            existing = {
                str(row["source_key"]): str(row["content_hash"])
                for row in connection.execute(
                    "SELECT source_key, content_hash FROM announcements "
                    "WHERE feed_item_key = ?",
                    (feed_item_key,),
                )
            }
            for season, source_key in zip(parsed.seasons, source_keys, strict=True):
                state = _library_state(
                    library, match.series.id, season, parsed.episode
                )
                is_new = (
                    source_key not in existing
                    or existing[source_key] != content_hash
                )
                connection.execute(
                    """
                    INSERT INTO announcements (
                        source_key, feed_item_key, feed_url, guid, link, title,
                        published_at, first_seen_at, last_seen_at, content_hash,
                        parsed_title, season, episode, imdb_id, matched_series_id,
                        matched_series_name, match_method, match_warning,
                        jellyfin_episode, jellyfin_episode_count,
                        jellyfin_expected_episode_count, is_current,
                        jellyfin_played_episode_count, needed_episodes,
                        status_reason, is_new
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_key) DO UPDATE SET
                        feed_item_key = excluded.feed_item_key,
                        feed_url = excluded.feed_url,
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
                        jellyfin_episode_count = excluded.jellyfin_episode_count,
                        jellyfin_expected_episode_count =
                            excluded.jellyfin_expected_episode_count,
                        is_current = excluded.is_current,
                        jellyfin_played_episode_count =
                            excluded.jellyfin_played_episode_count,
                        needed_episodes = excluded.needed_episodes,
                        status_reason = excluded.status_reason,
                        is_new = excluded.is_new
                    """,
                    (
                        source_key,
                        feed_item_key,
                        feed.feed_url,
                        feed.guid,
                        feed.link,
                        feed.title,
                        _iso(feed.published_at),
                        _iso(seen_at),
                        _iso(seen_at),
                        content_hash,
                        parsed.series_title,
                        season,
                        parsed.episode,
                        parsed.imdb_id,
                        match.series.id,
                        match.series.name,
                        match.method,
                        int(match.warning),
                        *state,
                        int(is_new),
                    ),
                )

            placeholders = ", ".join("?" for _ in source_keys)
            connection.execute(
                f"DELETE FROM announcements WHERE feed_item_key = ? "
                f"AND source_key NOT IN ({placeholders})",
                (feed_item_key, *source_keys),
            )

    def refresh_library_state(self, library: Library) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_key, matched_series_id, season, episode
                FROM announcements
                """
            ).fetchall()
            valid_ids = {series.id for series in library.series}
            for row in rows:
                series_id = row["matched_series_id"]
                season = row["season"]
                episode = row["episode"]
                if series_id not in valid_ids:
                    state = ReleaseState(None, 0, None, False, None, None, "removed")
                else:
                    state = _library_state(library, series_id, season, episode)
                connection.execute(
                    """
                    UPDATE announcements
                    SET jellyfin_episode = ?, jellyfin_episode_count = ?,
                        jellyfin_expected_episode_count = ?, is_current = ?,
                        jellyfin_played_episode_count = ?, needed_episodes = ?,
                        status_reason = ?
                    WHERE source_key = ?
                    """,
                    (
                        *state,
                        row["source_key"],
                    ),
                )

    def tracked_seasons(self) -> set[tuple[str, int]]:
        with self._connect() as connection:
            return {
                (str(row["matched_series_id"]), int(row["season"]))
                for row in connection.execute(
                    "SELECT DISTINCT matched_series_id, season FROM announcements"
                )
            }

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
            rows = [dict(row) for row in connection.execute(query).fetchall()]
        for row in rows:
            if row["needed_episodes"] is not None:
                row["needed_episodes"] = json.loads(row["needed_episodes"])
        return rows

    def state(self) -> dict[str, str]:
        with self._connect() as connection:
            return {
                row["key"]: row["value"]
                for row in connection.execute("SELECT key, value FROM app_state")
            }

    def observe_media_import(
        self, source_path: str, signature: str, seen_at: datetime, *, touch: bool = True
    ) -> tuple[datetime, bool, str]:
        """Record a source and return stable-since time, change flag and status."""
        now = _iso(seen_at)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT signature, first_seen_at, status FROM media_imports WHERE source_path = ?",
                (source_path,),
            ).fetchone()
            changed = row is None or str(row["signature"]) != signature
            first_seen = seen_at if changed else datetime.fromisoformat(row["first_seen_at"])
            if changed:
                connection.execute(
                    """
                    INSERT INTO media_imports (
                        source_path, signature, first_seen_at, last_seen_at, status, reason,
                        parsed_title, season, episode, target_path, transferred_at
                    ) VALUES (?, ?, ?, ?, 'waiting', 'Wartet auf Importprüfung', NULL, NULL, NULL, NULL, NULL)
                    ON CONFLICT(source_path) DO UPDATE SET
                        signature = excluded.signature,
                        first_seen_at = excluded.first_seen_at,
                        last_seen_at = excluded.last_seen_at,
                        status = 'waiting', reason = 'Wartet auf Importprüfung', parsed_title = NULL,
                        season = NULL, episode = NULL, target_path = NULL,
                        transferred_at = NULL
                    """,
                    (source_path, signature, now, now),
                )
            elif touch:
                connection.execute(
                    "UPDATE media_imports SET last_seen_at = ? WHERE source_path = ?",
                    (now, source_path),
                )
        status = "waiting" if changed else str(row["status"])
        return first_seen, changed, status

    def update_media_import(
        self,
        source_path: str,
        status: str,
        reason: str,
        *,
        parsed_title: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        target_path: str | None = None,
        transferred_at: datetime | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE media_imports SET status = ?, reason = ?, parsed_title = ?,
                    season = ?, episode = ?, target_path = ?, transferred_at = ?
                WHERE source_path = ?
                """,
                (
                    status,
                    reason,
                    parsed_title,
                    season,
                    episode,
                    target_path,
                    _iso(transferred_at) if transferred_at else None,
                    source_path,
                ),
            )

    def media_imports(self, limit: int = 300) -> list[dict[str, Any]]:
        with self._connect() as connection:
            active = connection.execute(
                """
                SELECT * FROM media_imports WHERE status != 'transferred'
                ORDER BY last_seen_at DESC
                """
            ).fetchall()
            transferred = connection.execute(
                """
                SELECT * FROM media_imports WHERE status = 'transferred'
                ORDER BY transferred_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in (*active, *transferred)]

    def media_import(self, source_path: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM media_imports WHERE source_path = ?", (source_path,)
            ).fetchone()
        return dict(row) if row is not None else None

    def media_import_target(self, source_path: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT target_path FROM media_imports WHERE source_path = ?",
                (source_path,),
            ).fetchone()
        if row is None or row["target_path"] is None:
            return None
        return str(row["target_path"])

    def forget_unseen_media_imports(self, seen_paths: set[str]) -> int:
        with self._connect() as connection:
            if seen_paths:
                placeholders = ", ".join("?" for _ in seen_paths)
                deleted = connection.execute(
                    f"DELETE FROM media_imports WHERE status != 'transferred' "
                    f"AND source_path NOT IN ({placeholders})",
                    tuple(sorted(seen_paths)),
                )
            else:
                deleted = connection.execute(
                    "DELETE FROM media_imports WHERE status != 'transferred'"
                )
        return deleted.rowcount

    def set_automatic_import_error(self, error: str) -> None:
        with self._connect() as connection:
            self._set_many(connection, {"automatic_import_error": error})

    def record_income_scan(self, completed_at: datetime, error: str = "") -> None:
        with self._connect() as connection:
            self._set_many(
                connection,
                {
                    "income_scan_at": _iso(completed_at),
                    "income_scan_error": error,
                },
            )

    def library_refresh_pending(self) -> bool:
        return self.state().get("library_refresh_pending") == "1"

    def set_library_refresh_pending(self, pending: bool) -> None:
        with self._connect() as connection:
            self._set_many(
                connection, {"library_refresh_pending": "1" if pending else "0"}
            )

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
    def _migrate_feed_item_keys(connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "SELECT * FROM announcements WHERE feed_item_key IS NULL"
        ).fetchall()
        if not rows:
            return

        columns = [
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(announcements)")
        ]
        placeholders = ", ".join("?" for _ in columns)
        column_names = ", ".join(columns)
        for row in rows:
            values = dict(row)
            feed_item_key = str(values["source_key"])
            parsed = parse_release(str(values["title"]))
            seasons = (
                tuple(parsed.seasons)
                if parsed is not None
                else (int(values["season"]),)
            )
            connection.execute(
                "DELETE FROM announcements WHERE source_key = ?",
                (values["source_key"],),
            )
            for season in seasons:
                migrated = dict(values)
                migrated["feed_item_key"] = feed_item_key
                migrated["source_key"] = _source_key(
                    feed_item_key, season, migrated["episode"]
                )
                migrated["season"] = season
                if len(seasons) > 1:
                    for name, value in (
                        ("jellyfin_episode", None),
                        ("jellyfin_episode_count", None),
                        ("jellyfin_expected_episode_count", None),
                        ("jellyfin_played_episode_count", None),
                        ("needed_episodes", None),
                        ("status_reason", None),
                        ("is_current", 1),
                    ):
                        migrated[name] = value
                connection.execute(
                    f"INSERT INTO announcements ({column_names}) "
                    f"VALUES ({placeholders})",
                    tuple(migrated[name] for name in columns),
                )

    @staticmethod
    def _set_many(connection: sqlite3.Connection, values: dict[str, str]) -> None:
        connection.executemany(
            """
            INSERT INTO app_state(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            values.items(),
        )

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _feed_item_key(feed: FeedRelease) -> str:
    identity = feed.guid or feed.link
    return hashlib.sha256(f"{feed.feed_url}\0{identity}".encode()).hexdigest()


def _source_key(
    feed_item_key: str, season: int, episode: int | None
) -> str:
    episode_key = "" if episode is None else str(episode)
    return hashlib.sha256(
        f"{feed_item_key}\0season:{season}\0episode:{episode_key}".encode()
    ).hexdigest()


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class ReleaseState(NamedTuple):
    highest_episode: int | None
    available_count: int
    expected_count: int | None
    is_current: bool
    played_count: int | None
    needed_episodes: str | None
    status_reason: str


def _library_state(
    library: Library, series_id: str, season: int, episode: int | None
) -> ReleaseState:
    highest_episode = library.episode_in_season(series_id, season)
    available_count, expected_count = library.season_counts(series_id, season)
    available = library.episode_numbers(series_id, season)
    played = library.played_numbers(series_id, season)
    required = (
        {episode}
        if episode is not None
        else library.expected_episodes.get((series_id, season))
    )
    needed = required - (available | played) if required else None
    if not required or needed:
        reason = "missing"
    elif required.issubset(available):
        reason = "available"
    elif required.issubset(played):
        reason = "played"
    else:
        reason = "covered"
    return ReleaseState(
        highest_episode,
        available_count,
        expected_count,
        reason == "missing",
        library.played_count(series_id, season),
        json.dumps(sorted(needed)) if needed is not None else None,
        reason,
    )
