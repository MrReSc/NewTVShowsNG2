from __future__ import annotations

import hashlib
import fcntl
import logging
import os
import re
import shutil
import stat
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from contextlib import contextmanager
from collections.abc import Iterator

from .config import Config
from .jellyfin import JellyfinClient, JellyfinError
from .matching import match_release
from .models import Library, ParsedRelease, RemoteSeries, Series
from .parsing import normalize_title, parse_release
from .storage import Storage

LOGGER = logging.getLogger(__name__)

VIDEO_SUFFIXES = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".webm",
}
IGNORED_VIDEO_PARTS = {"sample", "samples", "proof"}
UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
SAMPLE_TOKEN = re.compile(r"(?:^|[. _-])sample(?:$|[. _-])", re.IGNORECASE)
MULTI_EPISODE = re.compile(
    r"(?<![A-Za-z0-9])S\d{1,3}[.\s_-]*E\d{1,3}"
    r"(?:[.\s_+&-]*E\d{1,3}|[.\s_]*(?:-|to|bis)[.\s_]*(?:E)?\d{1,3})"
    r"(?!\d)",
    re.IGNORECASE,
)
SEASON_FOLDER = re.compile(
    r"^(?:Staffel|Season)\s*0*(?P<season>\d{1,3})$", re.IGNORECASE
)
INCOMPLETE_MARKER = ".newtvshowsng2-incomplete"
PROVIDER_ORDER = {"imdb": 0, "tvdb": 1, "tmdb": 2}
SUPPORTED_PROVIDERS = frozenset(PROVIDER_ORDER)


@dataclass(frozen=True, slots=True)
class ImportRunResult:
    transferred: int = 0
    blocked: int = 0
    waiting: int = 0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceUnit:
    path: Path
    video: Path
    signature: str


class MediaImporter:
    def __init__(
        self,
        config: Config,
        storage: Storage,
        jellyfin: JellyfinClient,
    ) -> None:
        self.config = config
        self.storage = storage
        self.jellyfin = jellyfin

    def observe(self, now: datetime | None = None) -> bool:
        """Record Income changes without importing files or contacting Jellyfin."""
        now = now or datetime.now(UTC)
        if not self.config.income_dir.is_dir():
            raise OSError(f"Income-Mount fehlt: {self.config.income_dir}")
        changed = False
        seen_paths: set[str] = set()
        for path in sorted(
            self.config.income_dir.iterdir(), key=lambda item: item.name.casefold()
        ):
            relative = path.relative_to(self.config.income_dir).as_posix()
            seen_paths.add(relative)
            signature = self._best_effort_signature(path)
            _, source_changed, _ = self.storage.observe_media_import(
                relative, signature, now, touch=False
            )
            changed |= source_changed
        removed = self.storage.forget_unseen_media_imports(seen_paths)
        return changed or removed > 0

    def has_work(self) -> bool:
        if self.storage.library_refresh_pending():
            return True
        if not self.config.income_dir.is_dir():
            return True
        return any(self.config.income_dir.iterdir())

    def run(
        self, library: Library, now: datetime | None = None, *, force: bool = False
    ) -> ImportRunResult:
        now = now or datetime.now(UTC)
        self._validate_mounts()
        self._validate_jellyfin_root()

        if self.storage.library_refresh_pending():
            try:
                self.jellyfin.refresh_library()
            except JellyfinError as exc:
                message = f"Ausstehender Jellyfin-Bibliotheksscan fehlgeschlagen: {exc}"
                LOGGER.warning("%s", message)
                return ImportRunResult(warnings=(message,))
            self.storage.set_library_refresh_pending(False)

        transferred = blocked = waiting = 0
        warnings: list[str] = []
        seen_paths: set[str] = set()
        new_series: dict[tuple[str, int | None, str | None], tuple[Path, str]] = {}
        new_series_paths: set[Path] = set()
        units = sorted(self.config.income_dir.iterdir(), key=lambda item: item.name.casefold())
        for path in units:
            relative = path.relative_to(self.config.income_dir).as_posix()
            seen_paths.add(relative)
            try:
                unit = self._inspect_source(path)
            except ImportBlocked as exc:
                signature = self._best_effort_signature(path)
                self.storage.observe_media_import(relative, signature, now)
                self.storage.update_media_import(relative, "blocked", str(exc))
                blocked += 1
                continue
            except OSError as exc:
                signature = self._best_effort_signature(path)
                self.storage.observe_media_import(relative, signature, now)
                message = f"Quelle konnte nicht vollständig gelesen werden: {exc}"
                self.storage.update_media_import(relative, "blocked", message)
                warnings.append(f"{relative}: {message}")
                blocked += 1
                continue

            first_seen, changed, old_status = self.storage.observe_media_import(
                relative, unit.signature, now
            )
            if old_status == "transferred" and not changed:
                stored_target = self.storage.media_import_target(relative)
                if stored_target:
                    try:
                        existing_target = _contained_path(
                            self.config.shows_dir,
                            self.config.shows_dir / stored_target,
                        )
                    except ImportBlocked:
                        existing_target = None
                    if existing_target is not None and existing_target.exists():
                        continue
            stable_at = first_seen + timedelta(hours=self.config.import_stable_hours)
            if not force and (changed or now < stable_at):
                self.storage.update_media_import(
                    relative,
                    "waiting",
                    "Wartet auf Stabilitätsfrist",
                )
                waiting += 1
                continue

            try:
                parsed = self._parse_source(unit)
            except ImportBlocked as exc:
                self.storage.update_media_import(relative, "blocked", str(exc))
                blocked += 1
                continue
            if parsed is None or parsed.episode is None or parsed.season != parsed.season_end:
                self.storage.update_media_import(
                    relative,
                    "blocked",
                    "Serie, Staffel und einzelne Episode konnten nicht eindeutig gelesen werden",
                )
                blocked += 1
                continue

            try:
                target_series, display_name, jellyfin_series = self._resolve_series(
                    parsed, library, new_series, new_series_paths
                )
                season_path = self._resolve_season_path(
                    target_series, parsed.season
                )
                self._ensure_episode_absent(
                    target_series,
                    season_path,
                    parsed,
                    library,
                    jellyfin_series,
                )
                target, transfer_warning = self._transfer(
                    unit, target_series, season_path
                )
            except ImportBlocked as exc:
                self.storage.update_media_import(
                    relative,
                    "blocked",
                    str(exc),
                    parsed_title=parsed.series_title,
                    season=parsed.season,
                    episode=parsed.episode,
                )
                blocked += 1
                continue
            except OSError as exc:
                message = f"Dateitransfer fehlgeschlagen: {exc}"
                self.storage.update_media_import(
                    relative,
                    "blocked",
                    message,
                    parsed_title=parsed.series_title,
                    season=parsed.season,
                    episode=parsed.episode,
                )
                warnings.append(f"{relative}: {message}")
                blocked += 1
                continue

            self.storage.update_media_import(
                relative,
                "transferred",
                transfer_warning or f"Nach {display_name} verschoben",
                parsed_title=parsed.series_title,
                season=parsed.season,
                episode=parsed.episode,
                target_path=target.relative_to(
                    self.config.shows_dir.resolve()
                ).as_posix(),
                transferred_at=now,
            )
            if transfer_warning:
                warnings.append(f"{relative}: {transfer_warning}")
            transferred += 1

        self.storage.forget_unseen_media_imports(seen_paths)
        if transferred:
            self.storage.set_library_refresh_pending(True)
            try:
                self.jellyfin.refresh_library()
            except JellyfinError as exc:
                message = f"Jellyfin-Bibliotheksscan nach Import fehlgeschlagen: {exc}"
                LOGGER.warning("%s", message)
                warnings.append(message)
            else:
                self.storage.set_library_refresh_pending(False)

        return ImportRunResult(transferred, blocked, waiting, tuple(warnings))

    def _validate_mounts(self) -> None:
        if not self.config.income_dir.is_dir():
            raise JellyfinError(f"Income-Mount fehlt: {self.config.income_dir}")
        if not self.config.shows_dir.is_dir():
            raise JellyfinError(f"Shows-Mount fehlt: {self.config.shows_dir}")
        if not os.access(self.config.income_dir, os.R_OK | os.W_OK | os.X_OK):
            raise JellyfinError(f"Income-Mount ist nicht les- und schreibbar: {self.config.income_dir}")
        if not os.access(self.config.shows_dir, os.R_OK | os.W_OK | os.X_OK):
            raise JellyfinError(f"Shows-Mount ist nicht les- und schreibbar: {self.config.shows_dir}")
        income = self.config.income_dir.resolve()
        shows = self.config.shows_dir.resolve()
        if income == shows or income in shows.parents or shows in income.parents:
            raise JellyfinError("Income- und Shows-Mount dürfen sich nicht überlappen")

    def _validate_jellyfin_root(self) -> None:
        expected = _clean_jellyfin_path(self.config.jellyfin_shows_path)
        locations = {
            _clean_jellyfin_path(value) for value in self.jellyfin.tv_library_locations()
        }
        if expected not in locations:
            raise JellyfinError(
                f"JELLYFIN_SHOWS_PATH {self.config.jellyfin_shows_path!r} ist kein "
                "Jellyfin-Serienbibliothekspfad"
            )

    def _inspect_source(self, path: Path) -> SourceUnit:
        if path.is_symlink():
            raise ImportBlocked("Symbolische Links werden nicht importiert")
        if path.is_file():
            if path.suffix.casefold() not in VIDEO_SUFFIXES:
                raise ImportBlocked("Kein unterstütztes Video oder Release-Ordner")
            return SourceUnit(path, path, _signature(path))
        if not path.is_dir():
            raise ImportBlocked("Nicht unterstützter Dateityp")

        videos: list[Path] = []
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ImportBlocked("Release-Ordner enthält einen symbolischen Link")
            if child.is_file() and child.suffix.casefold() in VIDEO_SUFFIXES:
                relative_parts = {part.casefold() for part in child.relative_to(path).parts[:-1]}
                if relative_parts & IGNORED_VIDEO_PARTS or SAMPLE_TOKEN.search(child.stem):
                    continue
                videos.append(child)
        if not videos:
            raise ImportBlocked("Release-Ordner enthält kein Hauptvideo")
        if len(videos) != 1:
            raise ImportBlocked("Release-Ordner enthält mehrere Hauptvideos")
        return SourceUnit(path, videos[0], _signature(path))

    def _parse_source(self, unit: SourceUnit) -> ParsedRelease | None:
        candidates = [unit.path.stem, unit.video.stem]
        parent = unit.video.parent
        while parent != unit.path and unit.path in parent.parents:
            candidates.append(parent.name)
            parent = parent.parent
        parsed_candidates: list[ParsedRelease] = []
        for candidate in dict.fromkeys(candidates):
            if MULTI_EPISODE.search(candidate):
                raise ImportBlocked("Mehrteilige Episodendateien werden nicht automatisch importiert")
            parsed = parse_release(candidate)
            if parsed is not None and parsed.episode is not None:
                parsed_candidates.append(parsed)
        if not parsed_candidates:
            return None
        episode_keys = {
            (item.season, item.season_end, item.episode) for item in parsed_candidates
        }
        if len(episode_keys) != 1:
            raise ImportBlocked(
                "Ordner- und Dateiname enthalten widersprüchliche Episodennummern"
            )
        title_keys = {item.normalized_title for item in parsed_candidates}
        explicit_years = {
            item.year for item in parsed_candidates if item.year is not None
        }
        if len(title_keys) != 1 or len(explicit_years) > 1:
            raise ImportBlocked(
                "Ordner- und Dateiname enthalten widersprüchliche Serienangaben"
            )
        return parsed_candidates[0]

    def _resolve_series(
        self,
        parsed: ParsedRelease,
        library: Library,
        new_series: dict[tuple[str, int | None, str | None], tuple[Path, str]],
        new_series_paths: set[Path],
    ) -> tuple[Path, str, Series | None]:
        match = match_release(parsed, library.series)
        if match is not None:
            if match.warning:
                raise ImportBlocked(
                    f"Bestehende Serie ist nicht eindeutig zugeordnet ({match.method})"
                )
            return (
                self._existing_series_path(match.series),
                match.series.name,
                match.series,
            )

        identity = (parsed.normalized_title, parsed.year, parsed.imdb_id)
        if identity in new_series:
            target, display_name = new_series[identity]
            return target, display_name, None

        remote = self._unique_remote_match(parsed)
        provider_matches = _series_with_remote_provider(remote, library.series)
        if len(provider_matches) > 1:
            raise ImportBlocked(
                "Jellyfin meldet die Provider-ID für mehrere bestehende Serien"
            )
        if provider_matches:
            series = provider_matches[0]
            return self._existing_series_path(series), series.name, series

        folder_name = _series_folder_name(remote)
        target = _safe_child(self.config.shows_dir, folder_name)
        if target.exists() and target not in new_series_paths:
            if not target.is_dir() or target.is_symlink() or not _directory_tree_empty(target):
                raise ImportBlocked(
                    "Neuer Serienordner kollidiert mit einem nicht von Jellyfin "
                    "zugeordneten Ordner"
                )
            new_series_paths.add(target)
        possible_existing = self._possible_existing_series(parsed, remote, new_series_paths)
        if possible_existing:
            raise ImportBlocked(
                "Möglicherweise vorhandener Serienordner ist Jellyfin nicht eindeutig "
                f"zugeordnet: {possible_existing.name}"
            )
        result = (target, remote.name)
        new_series[identity] = result
        new_series_paths.add(target)
        return target, remote.name, None

    def _existing_series_path(self, series: Series) -> Path:
        if not series.path:
            raise ImportBlocked("Jellyfin meldet für die bestehende Serie keinen Speicherpfad")
        root = PurePosixPath(_clean_jellyfin_path(self.config.jellyfin_shows_path))
        item = PurePosixPath(_clean_jellyfin_path(series.path))
        try:
            relative = item.relative_to(root)
        except ValueError as exc:
            raise ImportBlocked(
                "Jellyfin-Serienpfad liegt außerhalb des konfigurierten Shows-Pfads"
            ) from exc
        if not relative.parts:
            raise ImportBlocked("Jellyfin meldet keinen Serienunterordner")
        target = self.config.shows_dir.joinpath(*relative.parts)
        target = _contained_path(self.config.shows_dir, target)
        if not target.is_dir():
            raise ImportBlocked("Jellyfin-Serienpfad ist im Shows-Mount nicht vorhanden")
        return target

    def _possible_existing_series(
        self,
        parsed: ParsedRelease,
        remote: RemoteSeries,
        new_series_paths: set[Path],
    ) -> Path | None:
        wanted = {
            parsed.normalized_title,
            normalize_title(parsed.series_title),
            normalize_title(remote.name),
        }
        wanted.discard("")
        for child in self.config.shows_dir.iterdir():
            if child.name == ".newtvshowsng2-staging":
                continue
            resolved = _contained_path(self.config.shows_dir, child)
            if resolved in new_series_paths:
                continue
            if not child.is_dir():
                continue
            if wanted & _folder_title_variants(child.name):
                return child
        return None

    def _resolve_season_path(self, series_path: Path, season: int) -> Path:
        matches: list[Path] = []
        if series_path.is_dir():
            for child in series_path.iterdir():
                match = SEASON_FOLDER.fullmatch(child.name)
                if match is None or int(match.group("season")) != season:
                    continue
                if child.is_symlink():
                    raise ImportBlocked("Passender Staffelordner ist ein symbolischer Link")
                if not child.is_dir():
                    raise ImportBlocked("Ziel für den Staffelordner ist kein Verzeichnis")
                matches.append(_contained_path(self.config.shows_dir, child))
        if len(matches) > 1:
            raise ImportBlocked("Mehrere Ordner passen zur gleichen Staffel")
        if matches:
            return matches[0]
        return _contained_path(
            self.config.shows_dir, series_path / f"Staffel {season:02d}"
        )

    def _unique_remote_match(self, parsed: ParsedRelease) -> RemoteSeries:
        try:
            search_name = re.sub(r"[._]+", " ", parsed.series_title).strip()
            if parsed.year is not None:
                search_name = re.sub(
                    rf"\s*\(?{parsed.year}\)?\s*$", "", search_name
                ).strip()
            results = self.jellyfin.search_series(
                search_name, parsed.year, parsed.imdb_id
            )
        except JellyfinError as exc:
            raise ImportBlocked(f"Jellyfin-Metadatensuche fehlgeschlagen: {exc}") from exc

        identified: list[RemoteSeries] = []
        for result in results:
            ids = {
                key.casefold(): value.casefold()
                for key, value in result.provider_ids
                if key.casefold() in SUPPORTED_PROVIDERS
            }
            if not ids:
                continue
            if parsed.imdb_id and ids.get("imdb") != parsed.imdb_id.casefold():
                continue
            identified.append(result)

        if parsed.imdb_id:
            candidates = identified
        else:
            candidates = [
                item
                for item in identified
                if normalize_title(item.name) == parsed.normalized_title
                and (
                    parsed.year is None or item.production_year == parsed.year
                )
            ]
            full_title = normalize_title(parsed.series_title)
            if not candidates and full_title != parsed.normalized_title:
                candidates = [
                    item for item in identified if normalize_title(item.name) == full_title
                ]
            if not candidates and parsed.year is not None:
                # A single result with the requested year is useful for translated
                # Jellyfin titles, while multiple provider results remain blocked.
                candidates = [
                    item for item in identified if item.production_year == parsed.year
                ]

        identities = {
            (item.name, item.production_year, item.provider_ids): item for item in candidates
        }
        if len(identities) != 1:
            raise ImportBlocked(
                "Neue Serie konnte über Jellyfin nicht eindeutig mit Provider-ID bestimmt werden"
            )
        return next(iter(identities.values()))

    def _ensure_episode_absent(
        self,
        series_path: Path,
        season_path: Path,
        parsed: ParsedRelease,
        library: Library,
        jellyfin_series: Series | None,
    ) -> None:
        if jellyfin_series is not None and library.episode_exists(
            jellyfin_series.id, parsed.season, parsed.episode or -1
        ):
            raise ImportBlocked("Episode ist laut Jellyfin bereits vorhanden")

        if season_path.exists() and not season_path.is_dir():
            raise ImportBlocked("Ziel für den Staffelordner ist kein Verzeichnis")
        if series_path.is_dir():
            for video in series_path.rglob("*"):
                if not video.is_file() or video.suffix.casefold() not in VIDEO_SUFFIXES:
                    continue
                if _inside_owned_incomplete_import(video, series_path):
                    continue
                for existing in _parsed_path_context(video, series_path):
                    if (
                        existing.season == parsed.season
                        and existing.episode == parsed.episode
                    ):
                        raise ImportBlocked("Episode ist im Zielordner bereits vorhanden")

    def _transfer(
        self, unit: SourceUnit, series_path: Path, season_path: Path
    ) -> tuple[Path, str | None]:
        target = season_path / unit.path.name
        target = _contained_path(self.config.shows_dir, target)
        staging_root = _prepare_staging_root(self.config.shows_dir)

        with _exclusive_import_lock(staging_root):
            _recover_incomplete_target(target)
            if target.exists():
                raise ImportBlocked("Ein gleichnamiges Ziel existiert bereits")
            if _signature(unit.path) != unit.signature:
                raise ImportBlocked("Quelle hat sich vor dem Kopieren verändert")

            stage = staging_root / f"{uuid.uuid4().hex}-{unit.path.name}"
            stage_owned = False
            try:
                if unit.path.is_dir():
                    stage.mkdir(mode=0o700, exist_ok=False)
                    stage_owned = True
                    shutil.copytree(
                        unit.path,
                        stage,
                        dirs_exist_ok=True,
                        copy_function=shutil.copy2,
                    )
                else:
                    descriptor = os.open(
                        stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                    )
                    os.close(descriptor)
                    stage_owned = True
                    shutil.copy2(unit.path, stage)
                _verify_copy(unit.path, stage)
                _fsync_tree(stage)
                if _signature(unit.path) != unit.signature:
                    raise ImportBlocked("Quelle hat sich während des Kopierens verändert")
                _ensure_directory(series_path)
                _ensure_directory(season_path)
                if target.exists():
                    raise ImportBlocked(
                        "Ein gleichnamiges Ziel wurde während des Imports angelegt"
                    )
                # Store the scan intent before publication. If the process stops
                # immediately after the filesystem change, the next run still
                # refreshes Jellyfin 12.
                self.storage.set_library_refresh_pending(True)
                _publish_without_overwrite(stage, target)
            except BaseException:
                if stage_owned:
                    _remove_stage(stage)
                raise

            try:
                source_signature = _signature(unit.path)
            except FileNotFoundError:
                self.storage.set_library_refresh_pending(True)
                return target, (
                    "Ziel wurde vollständig übernommen; die Quelle war vor der "
                    "abschliessenden Entfernung bereits nicht mehr vorhanden"
                )
            except (OSError, ImportBlocked) as exc:
                self.storage.set_library_refresh_pending(True)
                return target, (
                    "Ziel wurde vollständig übernommen; die Quelle konnte vor dem "
                    f"Löschen nicht erneut geprüft werden und bleibt erhalten: {exc}"
                )

            if source_signature != unit.signature:
                self.storage.set_library_refresh_pending(True)
                return target, (
                    "Quelle hat sich nach dem Kopieren verändert. Quelle und geprüftes "
                    "Ziel bleiben zur manuellen Kontrolle erhalten"
                )

            # Persist the required Jellyfin refresh before the source can be
            # removed, so an interruption cannot lose that intent.
            self.storage.set_library_refresh_pending(True)
            source_warning = None
            try:
                if unit.path.is_dir():
                    shutil.rmtree(unit.path)
                else:
                    unit.path.unlink()
                _fsync_directory(unit.path.parent)
            except OSError as exc:
                source_warning = (
                    "Ziel wurde vollständig übernommen, die Quelle konnte aber nicht "
                    f"sicher entfernt und synchronisiert werden: {exc}"
                )
                LOGGER.error(
                    "Import wurde abgeschlossen, Quelle %s konnte aber nicht entfernt werden: %s",
                    unit.path,
                    exc,
                )
            return target, source_warning

    @staticmethod
    def _best_effort_signature(path: Path) -> str:
        try:
            return _signature(path)
        except (OSError, ImportBlocked):
            return "unreadable"


class ImportBlocked(RuntimeError):
    pass


def _signature(path: Path) -> str:
    digest = hashlib.sha256()
    items = [path] if path.is_file() else [path, *sorted(path.rglob("*"))]
    for item in items:
        relative = "." if item == path else item.relative_to(path).as_posix()
        details = item.lstat()
        if stat.S_ISLNK(details.st_mode):
            raise ImportBlocked("Symbolische Links werden nicht importiert")
        if not (stat.S_ISREG(details.st_mode) or stat.S_ISDIR(details.st_mode)):
            raise ImportBlocked("Quelle enthält einen nicht unterstützten Dateityp")
        digest.update(
            (
                f"{relative}\0{details.st_mode}\0{details.st_size}\0"
                f"{details.st_mtime_ns}\0{details.st_ctime_ns}\0"
                f"{details.st_dev}\0{details.st_ino}\n"
            ).encode(errors="surrogateescape")
        )
    return digest.hexdigest()


def _manifest(
    path: Path, ignored_relatives: frozenset[str] = frozenset()
) -> dict[str, tuple[str, int, str]]:
    items = [(".", path)] if path.is_file() else [
        (item.relative_to(path).as_posix(), item) for item in path.rglob("*")
    ]
    result: dict[str, tuple[str, int, str]] = {}
    for relative, item in items:
        if relative in ignored_relatives:
            continue
        details = item.lstat()
        if stat.S_ISLNK(details.st_mode):
            raise ImportBlocked("Kopie enthält unerwartet einen symbolischen Link")
        if stat.S_ISDIR(details.st_mode):
            result[relative] = ("directory", 0, "")
            continue
        if not stat.S_ISREG(details.st_mode):
            raise ImportBlocked("Kopie enthält einen nicht unterstützten Dateityp")
        result[relative] = ("file", details.st_size, _file_digest(item))
    return result


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_copy(
    source: Path,
    destination: Path,
    destination_markers: frozenset[str] = frozenset(),
) -> None:
    if _manifest(source) != _manifest(destination, destination_markers):
        raise OSError("Prüfsummenvergleich der kopierten Dateien ist fehlgeschlagen")


def _fsync_tree(path: Path) -> None:
    if path.is_file():
        files = [path]
        directories: list[Path] = []
    else:
        descendants = list(path.rglob("*"))
        files = [item for item in descendants if item.is_file()]
        directories = sorted(
            [path, *(item for item in descendants if item.is_dir())],
            key=lambda item: len(item.parts),
            reverse=True,
        )
    for item in files:
        with item.open("rb") as handle:
            os.fsync(handle.fileno())
    for directory in directories:
        _fsync_directory(directory)


def _remove_stage(path: Path) -> None:
    try:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    except OSError:
        LOGGER.exception("Zwischenstand %s konnte nicht bereinigt werden", path)


def _publish_without_overwrite(stage: Path, target: Path) -> None:
    """Publish staged content without ever replacing an existing target."""
    if stage.is_file():
        os.link(stage, target)
        _fsync_directory(target.parent)
        stage.unlink()
        return

    final_mode = stage.stat().st_mode & 0o777
    target.mkdir(mode=0o700, exist_ok=False)
    # Jellyfin 12 excludes a directory while a .ignore file is present. This
    # prevents its file watcher from observing a partially published release.
    marker = target / ".ignore"
    ownership_marker = target / INCOMPLETE_MARKER
    try:
        marker.touch(mode=0o600)
        ownership_marker.touch(mode=0o600)
        shutil.copytree(stage, target, dirs_exist_ok=True, copy_function=os.link)
        # copytree applies the source mode to the root. Keep it writable until
        # the private markers have been removed.
        target.chmod(0o700)
        _verify_copy(
            stage,
            target,
            frozenset({marker.name, ownership_marker.name}),
        )
        _fsync_tree(target)
        marker.unlink()
        _fsync_directory(target)
        ownership_marker.unlink()
        _set_directory_mode_and_fsync(target, final_mode)
        _fsync_directory(target.parent)
        shutil.rmtree(stage)
    except BaseException:
        # Never remove anything from the Shows tree automatically. The source
        # remains in Income and the private markers identify this target for
        # manual review.
        LOGGER.exception(
            "Unvollständiges Ziel %s bleibt zur manuellen Prüfung erhalten", target
        )
        raise


def _prepare_staging_root(shows_root: Path) -> Path:
    staging_root = shows_root / ".newtvshowsng2-staging"
    if staging_root.is_symlink():
        raise ImportBlocked("Staging-Verzeichnis ist ein symbolischer Link")
    created = False
    try:
        staging_root.mkdir(mode=0o750, exist_ok=False)
        created = True
    except FileExistsError:
        pass
    staging_root = _contained_path(shows_root, staging_root)
    if not staging_root.is_dir():
        raise ImportBlocked("Staging-Pfad ist kein Verzeichnis")
    ignore_file = staging_root / ".ignore"
    if ignore_file.is_symlink():
        raise ImportBlocked("Staging-.ignore ist ein symbolischer Link")
    if created:
        ignore_file.touch(mode=0o640)
    elif not ignore_file.is_file():
        raise ImportBlocked("Staging-.ignore ist keine Datei")
    return staging_root


@contextmanager
def _exclusive_import_lock(staging_root: Path) -> Iterator[None]:
    lock_path = staging_root / ".import.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o640)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _ensure_directory(path: Path) -> bool:
    if path.is_symlink():
        raise ImportBlocked(f"Zielverzeichnis ist ein symbolischer Link: {path.name}")
    try:
        path.mkdir(mode=0o750, exist_ok=False)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise ImportBlocked(f"Zielpfad ist kein sicheres Verzeichnis: {path.name}")
        return False
    return True


def _recover_incomplete_target(target: Path) -> None:
    if not target.is_dir() or target.is_symlink():
        return
    marker = target / ".ignore"
    ownership_marker = target / INCOMPLETE_MARKER
    if not (marker.is_file() and ownership_marker.is_file()):
        return
    raise ImportBlocked(
        "Ein früherer unvollständiger Import liegt im Ziel und muss manuell "
        "geprüft werden"
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _set_directory_mode_and_fsync(path: Path, mode: int) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _parsed_path_context(video: Path, series_path: Path) -> tuple[ParsedRelease, ...]:
    names = [video.stem]
    parent = video.parent
    while parent != series_path and series_path in parent.parents:
        names.append(parent.name)
        parent = parent.parent
    return tuple(
        parsed
        for name in dict.fromkeys(names)
        if (parsed := parse_release(name)) is not None and parsed.episode is not None
    )


def _inside_owned_incomplete_import(path: Path, boundary: Path) -> bool:
    parent = path.parent
    while parent != boundary and boundary in parent.parents:
        if (parent / ".ignore").is_file() and (
            parent / INCOMPLETE_MARKER
        ).is_file():
            return True
        parent = parent.parent
    return False


def _series_with_remote_provider(
    remote: RemoteSeries, series_items: list[Series]
) -> list[Series]:
    remote_ids = {
        key.casefold(): value.casefold()
        for key, value in remote.provider_ids
        if key.casefold() in SUPPORTED_PROVIDERS
    }
    if not remote_ids:
        return []
    matches: list[Series] = []
    for series in series_items:
        existing_ids = {
            key.casefold(): value.casefold()
            for key, value in series.provider_ids
            if key.casefold() in SUPPORTED_PROVIDERS
        }
        if series.imdb_id:
            existing_ids.setdefault("imdb", series.imdb_id.casefold())
        common = remote_ids.keys() & existing_ids.keys()
        equal = {key for key in common if remote_ids[key] == existing_ids[key]}
        conflicting = common - equal
        if equal and conflicting:
            raise ImportBlocked(
                f"Jellyfin meldet widersprüchliche Provider-IDs für {series.name}"
            )
        if equal:
            matches.append(series)
    return matches


def _folder_title_variants(name: str) -> set[str]:
    variants = {normalize_title(name)}
    without_ids = re.sub(
        r"\s*[\[{](?:imdb|tvdb|tmdb)(?:id)?[-:=][^\]}]+[\]}]\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    variants.add(normalize_title(without_ids))
    without_year = re.sub(
        r"\s*(?:\((?:19|20)\d{2}\)|(?:19|20)\d{2})\s*$",
        "",
        without_ids,
    ).strip()
    variants.add(normalize_title(without_year))
    variants.discard("")
    return variants


def _directory_tree_empty(path: Path) -> bool:
    try:
        return all(item.is_dir() and not item.is_symlink() for item in path.rglob("*"))
    except OSError:
        return False


def _series_folder_name(series: RemoteSeries) -> str:
    title = UNSAFE_NAME.sub(" - ", series.name)
    title = " ".join(title.split()).strip(" .")
    if not title:
        raise ImportBlocked("Jellyfin lieferte keinen sicheren Seriennamen")
    parts = [title]
    if series.production_year is not None:
        parts.append(f"({series.production_year})")
    provider_ids = sorted(
        (
            item
            for item in series.provider_ids
            if item[0].casefold() in SUPPORTED_PROVIDERS
        ),
        key=lambda item: (PROVIDER_ORDER.get(item[0].casefold(), 99), item[0].casefold()),
    )
    if not provider_ids:
        raise ImportBlocked("Jellyfin lieferte keine unterstützte Provider-ID")
    key, value = provider_ids[0]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ImportBlocked("Jellyfin lieferte eine unsichere Provider-ID")
    provider = key.casefold()
    label = {"imdb": "imdbid", "tvdb": "tvdbid", "tmdb": "tmdbid"}.get(
        provider, f"{provider}id"
    )
    parts.append(f"[{label}-{value}]")
    return " ".join(parts)


def _safe_child(parent: Path, name: str) -> Path:
    return _contained_path(parent, parent / name)


def _contained_path(root: Path, candidate: Path) -> Path:
    root_resolved = root.resolve()
    try:
        lexical_relative = candidate.absolute().relative_to(root.absolute())
    except ValueError as exc:
        raise ImportBlocked("Ermittelter Zielpfad liegt außerhalb des Shows-Mounts") from exc
    current = root
    for part in lexical_relative.parts:
        current = current / part
        if current.is_symlink():
            raise ImportBlocked("Zielpfad enthält einen symbolischen Link")
    candidate_resolved = candidate.resolve(strict=False)
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ImportBlocked("Ermittelter Zielpfad liegt außerhalb des Shows-Mounts") from exc
    return candidate_resolved


def _clean_jellyfin_path(value: str) -> str:
    clean = "/" + value.strip().replace("\\", "/").strip("/")
    return str(PurePosixPath(clean))
