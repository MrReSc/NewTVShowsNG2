from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Literal

from .config import Config
from .feeds import FeedClient, FeedError
from .jellyfin import JellyfinClient, JellyfinError
from .matching import match_release
from .media_importer import ImportRunResult, MediaImporter
from .models import Library, SeasonInventory
from .parsing import parse_release
from .rendering import Renderer
from .storage import Storage

LOGGER = logging.getLogger(__name__)
ManualRun = Literal["feed", "import"]
ScanRun = Literal["full", "feed", "import", "automatic_feed"]


class Scanner:
    def __init__(
        self,
        config: Config,
        storage: Storage,
        renderer: Renderer,
        jellyfin: JellyfinClient | None = None,
        feeds: FeedClient | None = None,
        importer: MediaImporter | None = None,
    ) -> None:
        self.config = config
        self.storage = storage
        self.renderer = renderer
        self.jellyfin = jellyfin or JellyfinClient(
            config.jellyfin_url,
            config.jellyfin_api_key,
            config.jellyfin_username,
            config.request_timeout,
        )
        self.feeds = feeds or FeedClient(config.request_timeout)
        self.importer = importer
        if self.importer is None and config.media_import_enabled:
            self.importer = MediaImporter(config, storage, self.jellyfin)
        self._lock = threading.Lock()

    def run(self) -> bool:
        with self._lock:
            started_at = datetime.now(UTC)
            self._begin_run("full", started_at)
            return self._run_locked("full", started_at)

    def run_feed(self) -> bool:
        with self._lock:
            started_at = datetime.now(UTC)
            self._begin_run("automatic_feed", started_at)
            return self._run_locked("automatic_feed", started_at)

    def run_scheduled_import(self) -> bool:
        if self.importer is None or not self.config.media_import_enabled:
            return False
        with self._lock:
            try:
                if not self.importer.has_work():
                    if self.storage.state().get("automatic_import_error"):
                        self.storage.set_automatic_import_error("")
                        self.renderer.render()
                    return False
                result = self._import_media(
                    self.jellyfin.load_library(), datetime.now(UTC), force=False
                )
                self.storage.set_automatic_import_error("\n".join(result.warnings))
                self.renderer.render()
                return True
            except Exception as exc:
                LOGGER.exception("Automatischer Medienimport fehlgeschlagen: %s", exc)
                self.storage.set_automatic_import_error(str(exc))
                try:
                    self.renderer.render()
                except Exception:
                    LOGGER.exception("Importfehler konnte nicht angezeigt werden")
                return False

    def scan_income(self) -> bool | None:
        if self.importer is None or not self.config.media_import_enabled:
            raise ValueError("Medienimport ist deaktiviert")
        if not self._lock.acquire(blocking=False):
            return None
        try:
            changed = self.importer.observe()
            self.storage.record_income_scan(datetime.now(UTC))
            self.renderer.render()
            return changed
        except Exception as exc:
            LOGGER.exception("Income-Scan fehlgeschlagen: %s", exc)
            self.storage.record_income_scan(datetime.now(UTC), str(exc))
            try:
                self.renderer.render()
            except Exception:
                LOGGER.exception("Income-Scanfehler konnte nicht angezeigt werden")
            raise
        finally:
            self._lock.release()

    def start_manual(self, kind: ManualRun) -> bool:
        if kind not in ("feed", "import"):
            raise ValueError(f"Unbekannte Laufart: {kind}")
        if kind == "import" and (
            not self.config.media_import_enabled or self.importer is None
        ):
            raise ValueError("Medienimport ist deaktiviert")
        if not self._lock.acquire(blocking=False):
            return False

        try:
            started_at = datetime.now(UTC)
            self._begin_run(kind, started_at)
            self.renderer.render()
            worker = threading.Thread(
                target=self._manual_worker,
                args=(kind, started_at),
                name=f"manual-{kind}",
                daemon=True,
            )
            worker.start()
        except Exception as exc:
            try:
                if kind == "import":
                    self.storage.fail_manual_import(datetime.now(UTC), str(exc))
                else:
                    self.storage.fail_scan(datetime.now(UTC), None, str(exc))
                self.renderer.render()
            except Exception:
                LOGGER.exception("Startfehler konnte nicht angezeigt werden")
            finally:
                self._lock.release()
            raise
        return True

    def _manual_worker(self, kind: ManualRun, started_at: datetime) -> None:
        try:
            self._run_locked(kind, started_at)
        finally:
            self._lock.release()

    def _begin_run(self, kind: ScanRun, started_at: datetime) -> None:
        if kind == "import":
            self.storage.begin_manual_import(started_at)
            return
        next_run = (
            started_at + timedelta(seconds=self.config.interval_seconds)
            if kind in ("full", "automatic_feed")
            else None
        )
        self.storage.begin_scan(started_at, next_run, manual=kind == "feed")

    def _run_locked(self, kind: ScanRun, started_at: datetime) -> bool:
        try:
            library = self.jellyfin.load_library()
            if kind == "import":
                result = self._import_media(library, started_at, force=True)
                summary = (
                    f"{result.transferred} übernommen, {result.blocked} blockiert, "
                    f"{result.waiting} wartend"
                )
                self.storage.complete_manual_import(
                    datetime.now(UTC), summary, list(result.warnings)
                )
                self.renderer.render()
                return True

            scan_warnings: list[str] = []
            if kind == "full" and self.importer is not None:
                import_result = self._import_media(library, started_at, force=False)
                scan_warnings.extend(import_result.warnings)
            season_cache: set[tuple[str, int]] = set()
            series_cache: dict[str, dict[int, SeasonInventory] | None] = {}
            missing_metadata_warning_logged = False

            def load_season(series_id: str, season: int) -> None:
                nonlocal missing_metadata_warning_logged
                key = (series_id, season)
                if key in season_cache:
                    return
                season_cache.add(key)

                if series_id not in series_cache:
                    try:
                        series_cache[series_id] = self.jellyfin.load_series_episodes(
                            series_id
                        )
                    except JellyfinError as exc:
                        series_cache[series_id] = None
                        message = (
                            f"Jellyfin-Sollzahl und Gesehen-Status für {series_id} "
                            f"konnten nicht geladen werden: {exc}"
                        )
                        scan_warnings.append(message)
                        LOGGER.warning("%s", message)
                inventories = series_cache[series_id]
                if inventories is None:
                    return
                inventory = inventories.get(season, SeasonInventory())
                library.set_played_episodes(
                    series_id,
                    season,
                    inventory.played,
                    complete=bool(inventory.episodes)
                    and inventory.played_status_complete,
                )
                if not inventory.played_status_complete:
                    message = (
                        f"Jellyfin-Gesehen-Status für {series_id} S{season:02d} "
                        "ist unvollständig; nur bestätigte Gesehen-Markierungen gelten"
                    )
                    scan_warnings.append(message)
                    LOGGER.warning("%s", message)

                if not library.missing_episode_tracking_enabled:
                    if not missing_metadata_warning_logged:
                        message = (
                            "Jellyfin importiert keine fehlenden Episoden; "
                            "Sollzahlen von Staffeln bleiben unbekannt"
                        )
                        scan_warnings.append(message)
                        LOGGER.warning("%s", message)
                        missing_metadata_warning_logged = True
                    return

                local_episodes = library.episode_numbers(series_id, season)
                expected_episodes = inventory.episodes

                if not local_episodes.issubset(expected_episodes):
                    message = (
                        f"Jellyfin lieferte widersprüchliche Episodendaten für "
                        f"{series_id} S{season:02d}; Sollzahl bleibt unbekannt"
                    )
                    scan_warnings.append(message)
                    LOGGER.warning("%s", message)
                    return
                library.set_expected_episodes(series_id, season, expected_episodes)

            valid_series_ids = {series.id for series in library.series}
            for series_id, season in self.storage.tracked_seasons():
                if series_id in valid_series_ids:
                    load_season(series_id, season)
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
                    for season in parsed.seasons:
                        load_season(match.series.id, season)
                    self.storage.upsert_release(
                        feed_release, parsed, match, library, started_at
                    )

            if successful_feeds == 0:
                raise RuntimeError("Keiner der konfigurierten RSS-Feeds war erreichbar")

            self.storage.prune(self.config.max_history)
            completed_at = datetime.now(UTC)
            next_run = (
                completed_at + timedelta(seconds=self.config.interval_seconds)
                if kind in ("full", "automatic_feed")
                else None
            )
            self.storage.complete_scan(
                completed_at, next_run, [*feed_errors, *scan_warnings]
            )
            self.renderer.render()
            LOGGER.info(
                "Scan abgeschlossen%s",
                f" ({len(feed_errors)} Feed-Fehler)" if feed_errors else "",
            )
            return True
        except Exception as exc:
            failed_at = datetime.now(UTC)
            message = str(exc)
            LOGGER.exception(
                "%s fehlgeschlagen: %s",
                "Import" if kind == "import" else "Scan",
                message,
            )
            if kind == "import":
                self.storage.fail_manual_import(failed_at, message)
            else:
                next_run = (
                    failed_at + timedelta(seconds=self.config.interval_seconds)
                    if kind in ("full", "automatic_feed")
                    else None
                )
                self.storage.fail_scan(failed_at, next_run, message)
            try:
                self.renderer.render()
            except Exception:
                LOGGER.exception("Fehlerseite konnte nicht geschrieben werden")
            return False

    def _import_media(
        self, library: Library, started_at: datetime, *, force: bool
    ) -> ImportRunResult:
        assert self.importer is not None
        result = self.importer.run(library, started_at, force=force)
        LOGGER.info(
            "Medienimport: %d übernommen, %d blockiert, %d wartend",
            result.transferred,
            result.blocked,
            result.waiting,
        )
        return result
