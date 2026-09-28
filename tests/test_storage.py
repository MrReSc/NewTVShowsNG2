import sqlite3

from newtvshowsng2.storage import Storage

LEGACY_SCHEMA = """
CREATE TABLE announcements (
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
CREATE TABLE app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def test_initialize_migrates_existing_database_without_data_loss(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(LEGACY_SCHEMA)
        connection.execute(
            """
            INSERT INTO announcements (
                source_key, feed_url, link, title, published_at, first_seen_at,
                last_seen_at, content_hash, parsed_title, season,
                matched_series_id, matched_series_name, match_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "source",
                "https://feed.test/rss",
                "https://feed.test/release",
                "Show.S03",
                "2026-09-10T00:00:00+00:00",
                "2026-09-10T00:00:00+00:00",
                "2026-09-10T00:00:00+00:00",
                "hash",
                "Show",
                3,
                "show",
                "Show",
                "Titel",
            ),
        )

    storage = Storage(path)
    storage.initialize()
    storage.initialize()

    with sqlite3.connect(path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(announcements)")
        }
        title = connection.execute("SELECT title FROM announcements").fetchone()[0]
    assert "jellyfin_episode_count" in columns
    assert "jellyfin_expected_episode_count" in columns
    assert {
        "jellyfin_played_episode_count",
        "needed_episodes",
        "status_reason",
        "feed_item_key",
    } <= columns
    assert title == "Show.S03"
    row = storage.announcements()[0]
    assert row["jellyfin_played_episode_count"] is None
    assert row["needed_episodes"] is None
    assert row["status_reason"] is None
    with sqlite3.connect(path) as connection:
        assert {
            r[0]
            for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        } == {"announcements", "app_state", "media_imports"}


def test_initialize_expands_legacy_season_range_idempotently(tmp_path) -> None:
    path = tmp_path / "legacy-range.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(LEGACY_SCHEMA)
        connection.execute(
            """
            INSERT INTO announcements (
                source_key, feed_url, link, title, published_at, first_seen_at,
                last_seen_at, content_hash, parsed_title, season,
                matched_series_id, matched_series_name, match_method,
                jellyfin_episode, is_current, is_new
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-source",
                "https://feed.test/rss",
                "https://feed.test/outlander",
                "Outlander.S05.-.S08.Complete.German",
                "2026-09-10T00:00:00+00:00",
                "2026-09-10T01:00:00+00:00",
                "2026-09-10T02:00:00+00:00",
                "hash",
                "Outlander",
                5,
                "outlander",
                "Outlander",
                "Titel",
                12,
                0,
                0,
            ),
        )

    storage = Storage(path)
    storage.initialize()
    storage.initialize()

    rows = storage.announcements()
    assert {row["season"] for row in rows} == {5, 6, 7, 8}
    assert len(rows) == 4
    assert {row["feed_item_key"] for row in rows} == {"legacy-source"}
    assert len({row["source_key"] for row in rows}) == 4
    assert all(row["link"] == "https://feed.test/outlander" for row in rows)
    assert all(row["first_seen_at"] == "2026-09-10T01:00:00+00:00" for row in rows)
    assert all(row["jellyfin_episode"] is None for row in rows)
    assert all(row["is_current"] for row in rows)
