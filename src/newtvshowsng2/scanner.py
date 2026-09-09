from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta

from .config import Config
from .feeds import FeedClient, FeedError
from .jellyfin import JellyfinClient
from .matching import match_release
from .parsing import parse_release
from .rendering import Renderer
from .storage import Storage

LOGGER = logging.getLogger(__name__)


class Scanner:
    def __init__(
        self,
        config: Config,
        storage: Storage,
        renderer: Renderer,
        jellyfin: JellyfinClient | None = None,
        feeds: FeedClient | None = None,
    ) -> None:
        self.config = config
        self.storage = storage
        self.renderer = renderer
        self.jellyfin = jellyfin or JellyfinClient(
            config.jellyfin_url, config.jellyfin_api_key, config.request_timeout
        )
        self.feeds = feeds or FeedClient(config.request_timeout)
        self._lock = threading.Lock()

    def run(self) -> bool:
        if not self._lock.acquire(blocking=False):
            LOGGER.warning("Scan übersprungen: Ein anderer Lauf ist noch aktiv")
            return False

        started_at = datetime.now(UTC)
        planned_next = started_at + timedelta(seconds=self.config.interval_seconds)
        self.storage.begin_scan(started_at, planned_next)
        try:
            library = self.jellyfin.load_library()
            self.storage.refresh_library_state(library)
            feed_errors: list[str] = []
            successful_feeds = 0

            for feed_url in self.config.rss_urls:
                try:
                    releases = self.feeds.load(feed_url)
                    successful_feeds += 1
                except FeedError as exc:
                    message = f"{feed_url}: {exc}"
                    feed_errors.append(message)
                    LOGGER.error("RSS-Fehler: %s", message)
                    continue

                for feed_release in releases:
                    parsed = parse_release(feed_release.title, feed_release.content)
                    if parsed is None:
                        LOGGER.debug("Kein Sxx-Muster: %s", feed_release.title)
                        continue
                    match = match_release(parsed, library.series)
                    if match is None:
                        LOGGER.info(
                            "Keine Jellyfin-Serie für RSS-Titel %r (bereinigt: %r)",
                            feed_release.title,
                            parsed.normalized_title,
                        )
                        continue
                    if match.warning:
                        LOGGER.warning(
                            "Unsichere Zuordnung: %r -> %r (%s)",
                            feed_release.title,
                            match.series.name,
                            match.method,
                        )
                    self.storage.upsert_release(
                        feed_release, parsed, match, library, started_at
                    )

            if successful_feeds == 0:
                raise RuntimeError("Keiner der konfigurierten RSS-Feeds war erreichbar")

            self.storage.prune(self.config.max_history)
            completed_at = datetime.now(UTC)
            next_run = completed_at + timedelta(seconds=self.config.interval_seconds)
            self.storage.complete_scan(completed_at, next_run, feed_errors)
            self.renderer.render()
            LOGGER.info(
                "Scan abgeschlossen%s",
                f" ({len(feed_errors)} Feed-Fehler)" if feed_errors else "",
            )
            return True
        except Exception as exc:
            failed_at = datetime.now(UTC)
            next_run = failed_at + timedelta(seconds=self.config.interval_seconds)
            message = str(exc)
            LOGGER.exception("Scan fehlgeschlagen: %s", message)
            self.storage.fail_scan(failed_at, next_run, message)
            try:
                self.renderer.render()
            except Exception:
                LOGGER.exception("Fehlerseite konnte nicht geschrieben werden")
            return False
        finally:
            self._lock.release()
