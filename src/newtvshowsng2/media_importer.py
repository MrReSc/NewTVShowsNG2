from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import stat
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from . import filesystem
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


@dataclass(frozen=True, slots=True)
class SeriesChoice:
    remote: RemoteSeries
    key: str
    imdb_url: str | None
    existing_series: Series | None = None


@dataclass(frozen=True, slots=True)
class SelectionOptions:
    source_path: str
    signature: str
    parsed: ParsedRelease
    choices: tuple[SeriesChoice, ...]


@dataclass(frozen=True, slots=True)
class SelectedSeries:
    source_path: str
    signature: str
    parsed: ParsedRelease
    remote: RemoteSeries
    existing_series_id: str | None = None


class SelectionUnavailable(ValueError):
    pass


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
        protected = self.recover_moves()
        changed = False
        seen_paths: set[str] = set()
        for path in sorted(
            self.config.income_dir.iterdir(), key=lambda item: item.name.casefold()
        ):
            relative = path.relative_to(self.config.income_dir).as_posix()
            seen_paths.add(relative)
            if relative in protected:
                continue
            signature = self._best_effort_signature(path)
            _, source_changed, _ = self.storage.observe_media_import(
                relative, signature, now, touch=False
            )
            changed |= source_changed
        removed = self.storage.forget_unseen_media_imports(seen_paths)
        return changed or removed > 0

    def has_work(self) -> bool:
        if self.storage.library_refresh_pending() or self.storage.pending_media_moves():
            return True
        if not self.config.income_dir.is_dir():
            return True
        return any(self.config.income_dir.iterdir())

    def selection_options(self, source_path: str) -> SelectionOptions:
        if (
            not source_path
            or source_path in (".", "..")
            or Path(source_path).name != source_path
            or "\x00" in source_path
        ):
            raise SelectionUnavailable("Ungültiger Income-Eintrag")
        row = self.storage.media_import(source_path)
        if row is None or row["status"] != "needs_selection":
            raise SelectionUnavailable("Für diesen Eintrag ist keine Serienauswahl offen")
        path = self.config.income_dir / source_path
        try:
            unit = self._inspect_source(path)
            parsed = self._parse_source(unit)
        except (OSError, ImportBlocked) as exc:
            raise SelectionUnavailable(
                f"Income-Eintrag konnte nicht geprüft werden: {exc}"
            ) from exc
        if unit.signature != row["signature"]:
            raise SelectionUnavailable(
                "Income-Eintrag wurde verändert; bitte Importprüfung erneut starten"
            )
        if parsed is None or parsed.episode is None or parsed.season != parsed.season_end:
            raise SelectionUnavailable("Serie und Episode sind nicht mehr eindeutig lesbar")
        results = self._remote_search_results(parsed)
        candidates = self._remote_candidates(parsed, results=results)
        if not candidates and len(results) == 1:
            library = self.jellyfin.load_library()
            try:
                choice = self._existing_series_choice(parsed, results, library)
            except ImportBlocked as exc:
                raise SelectionUnavailable(str(exc)) from exc
            if choice is not None:
                return SelectionOptions(source_path, unit.signature, parsed, (choice,))
        if len(candidates) < 2:
            raise SelectionUnavailable("Jellyfin meldet keine passende Serienauswahl mehr")
        choices = tuple(
            SeriesChoice(remote, _choice_key(remote), _imdb_url(remote))
            for remote in candidates
        )
        return SelectionOptions(source_path, unit.signature, parsed, choices)

    def select_series(
        self, source_path: str, signature: str, choice_key: str
    ) -> SelectedSeries:
        options = self.selection_options(source_path)
        if options.signature != signature:
            raise SelectionUnavailable(
                "Income-Eintrag wurde verändert; bitte Auswahl neu öffnen"
            )
        matches = [choice for choice in options.choices if choice.key == choice_key]
        if len(matches) != 1:
            raise SelectionUnavailable(
                "Jellyfin-Suchergebnis wurde verändert; bitte Auswahl neu öffnen"
            )
        choice = matches[0]
        return SelectedSeries(
            source_path, signature, options.parsed, choice.remote,
            choice.existing_series.id if choice.existing_series is not None else None,
        )

    def run(
        self, library: Library, now: datetime | None = None, *,
        force: bool = False, selection: SelectedSeries | None = None,
    ) -> ImportRunResult:
        now = now or datetime.now(UTC)
        self._validate_mounts()
        protected = self.recover_moves()
        self._validate_jellyfin_root()

        if selection is not None:
            selected_source = self.config.income_dir / selection.source_path
            try:
                current = self._inspect_source(selected_source)
                current_parsed = self._parse_source(current)
            except (OSError, ImportBlocked) as exc:
                raise SelectionUnavailable(f"Income-Eintrag wurde verändert: {exc}") from exc
            if current.signature != selection.signature or current_parsed != selection.parsed:
                raise SelectionUnavailable(
                    "Income-Eintrag wurde verändert; bitte Auswahl neu öffnen"
                )

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
        if selection is not None:
            units = [path for path in units if self._belongs_to_selection(path, selection)]
            units.sort(
                key=lambda path: (path.name != selection.source_path, path.name.casefold())
            )
        for path in units:
            relative = path.relative_to(self.config.income_dir).as_posix()
            seen_paths.add(relative)
            if relative in protected:
                blocked += 1
                continue
            try:
                unit = self._inspect_source(path)
            except ImportBlocked as exc:
                signature = self._best_effort_signature(path)
                self.storage.observe_media_import(relative, signature, now)
                self._record_block(relative, str(exc))
                blocked += 1
                continue
            except OSError as exc:
                signature = self._best_effort_signature(path)
                self.storage.observe_media_import(relative, signature, now)
                message = f"Quelle konnte nicht vollständig gelesen werden: {exc}"
                self._record_block(relative, message)
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
                self._record_block(relative, str(exc))
                blocked += 1
                continue
            if parsed is None or parsed.episode is None or parsed.season != parsed.season_end:
                self._record_block(
                    relative,
                    "Serie, Staffel und einzelne Episode konnten nicht eindeutig gelesen werden",
                )
                blocked += 1
                continue

            try:
                target_series, display_name, jellyfin_series = self._resolve_series(
                    parsed, library, new_series, new_series_paths,
                    selected_remote=selection.remote if selection is not None else None,
                    selected_series_id=(
                        selection.existing_series_id if selection is not None else None
                    ),
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
            except ImportWaiting as exc:
                self.storage.update_media_import(
                    relative, "waiting", str(exc), parsed_title=parsed.series_title,
                    season=parsed.season, episode=parsed.episode,
                )
                waiting += 1
                continue
            except ImportSelectionRequired as exc:
                self._record_block(
                    relative, str(exc), status="needs_selection", parsed_title=parsed.series_title,
                    season=parsed.season, episode=parsed.episode,
                )
                blocked += 1
                continue
            except ImportBlocked as exc:
                self._record_block(
                    relative,
                    str(exc),
                    parsed_title=parsed.series_title,
                    season=parsed.season,
                    episode=parsed.episode,
                )
                blocked += 1
                continue
            except OSError as exc:
                message = f"Dateitransfer fehlgeschlagen: {exc}"
                self._record_block(
                    relative,
                    message,
                    parsed_title=parsed.series_title,
                    season=parsed.season,
                    episode=parsed.episode,
                )
                warnings.append(f"{relative}: {message}")
                blocked += 1
                continue

            if transfer_warning:
                warnings.append(f"{relative}: {transfer_warning}")
            transferred += 1

        if selection is None:
            blocked += len(protected - seen_paths)
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

    def _record_block(
        self, source_path: str, reason: str, *, status: str = "blocked",
        parsed_title: str | None = None, season: int | None = None,
        episode: int | None = None,
    ) -> None:
        previous = self.storage.media_import(source_path)
        self.storage.update_media_import(
            source_path, status, reason, parsed_title=parsed_title,
            season=season, episode=episode,
        )
        if previous is None or previous["status"] != status or previous["reason"] != reason:
            LOGGER.warning("Medienimport: %s blockiert: %s", source_path, reason)

    def _belongs_to_selection(self, path: Path, selection: SelectedSeries) -> bool:
        if path.name == selection.source_path:
            return True
        try:
            parsed = self._parse_source(self._inspect_source(path))
        except (OSError, ImportBlocked):
            return False
        if parsed is None or parsed.normalized_title != selection.parsed.normalized_title:
            return False
        if parsed.year is not None and parsed.year != selection.remote.production_year:
            return False
        remote_imdb = _provider_id(selection.remote, "imdb")
        return not parsed.imdb_id or parsed.imdb_id.casefold() == (
            remote_imdb or ""
        ).casefold()

    def _validate_mounts(self) -> None:
        try:
            filesystem.preflight(self.config.income_dir, self.config.shows_dir)
        except (filesystem.FilesystemBlocked, OSError, ValueError, KeyError) as exc:
            raise JellyfinError(f"Vorprüfung für atomaren Import fehlgeschlagen: {exc}") from exc
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
        *,
        selected_remote: RemoteSeries | None = None,
        selected_series_id: str | None = None,
    ) -> tuple[Path, str, Series | None]:
        if selected_series_id is not None:
            series = next(
                (item for item in library.series if item.id == selected_series_id), None
            )
            if series is None:
                raise ImportBlocked("Gewählte Jellyfin-Serie ist nicht mehr vorhanden")
            provider_matches = (
                _series_with_remote_provider(selected_remote, library.series)
                if selected_remote is not None else []
            )
            if len(provider_matches) != 1 or provider_matches[0].id != series.id:
                raise ImportBlocked(
                    "Gewählte Jellyfin-Serie stimmt nicht mehr mit den Provider-IDs überein"
                )
            if parsed.year is not None and parsed.year != series.production_year:
                raise ImportBlocked("Jellyfin-Serienjahr widerspricht dem Release-Jahr")
            return self._existing_series_path(series), series.name, series

        match = match_release(parsed, library.series)
        if match is not None:
            if match.warning:
                raise ImportBlocked(
                    f"Bestehende Serie ist nicht eindeutig zugeordnet ({match.method})"
                )
            if selected_remote is not None and match.series not in _series_with_remote_provider(
                selected_remote, library.series
            ):
                raise ImportBlocked("Jellyfin-Serie widerspricht der gewählten Provider-ID")
            return (
                self._existing_series_path(match.series),
                match.series.name,
                match.series,
            )

        identity = (parsed.normalized_title, parsed.year, parsed.imdb_id)
        if identity in new_series:
            target, display_name = new_series[identity]
            return target, display_name, None

        candidates = None
        if selected_remote is None:
            search_error = None
            if library.series:
                try:
                    results = self._remote_search_results(parsed)
                except ImportBlocked as exc:
                    # Ein API-Ausfall soll die bisherige Warteprüfung nicht verändern.
                    search_error = exc
                else:
                    candidates = self._remote_candidates(parsed, results=results)
                    if not candidates and self._existing_series_choice(
                        parsed, results, library
                    ) is not None:
                        raise ImportSelectionRequired(
                            "Jellyfin-Titel weicht vom Release-Titel ab. "
                            "Vorhandene Serie bitte bestätigen"
                        )
            pending = self._pending_jellyfin_folder(parsed)
            if pending is not None:
                raise ImportWaiting(
                    f"Wartet auf Jellyfin-Bibliothekseintrag für {pending.name}"
                )
            if search_error is not None:
                raise search_error
        remote = selected_remote or self._unique_remote_match(parsed, candidates=candidates)
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

    def _pending_jellyfin_folder(self, parsed: ParsedRelease) -> Path | None:
        for child in self.config.shows_dir.iterdir():
            if not child.is_dir() or child.is_symlink():
                continue
            if not re.search(
                r"\[(?:imdb|tvdb|tmdb)id-[A-Za-z0-9._-]+\]$",
                child.name,
                flags=re.IGNORECASE,
            ):
                continue
            if parsed.normalized_title not in _folder_title_variants(child.name):
                continue
            year_match = re.search(r"\(((?:19|20)\d{2})\)\s+\[", child.name)
            if parsed.year is not None and (
                year_match is None or int(year_match.group(1)) != parsed.year
            ):
                continue
            if _directory_tree_empty(child):
                continue
            return child
        return None

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

    def _unique_remote_match(
        self, parsed: ParsedRelease, *, candidates: list[RemoteSeries] | None = None
    ) -> RemoteSeries:
        if candidates is None:
            candidates = self._remote_candidates(parsed)
        if len(candidates) > 1:
            raise ImportSelectionRequired(
                "Neue Serie ist nicht eindeutig zugeordnet; mehrere Jellyfin-Treffer passen"
            )
        if not candidates:
            raise ImportBlocked(
                "Neue Serie konnte über Jellyfin nicht eindeutig mit Provider-ID bestimmt werden"
            )
        return candidates[0]

    def _existing_series_choice(
        self, parsed: ParsedRelease, results: list[RemoteSeries], library: Library
    ) -> SeriesChoice | None:
        if len(results) != 1:
            return None
        remote = results[0]
        if parsed.year is not None and parsed.year != remote.production_year:
            return None
        if parsed.imdb_id and parsed.imdb_id.casefold() != (
            _provider_id(remote, "imdb") or ""
        ).casefold():
            return None
        matches = _series_with_remote_provider(remote, library.series)
        if len(matches) != 1:
            return None
        series = matches[0]
        if parsed.year is not None and parsed.year != series.production_year:
            return None
        return SeriesChoice(
            remote, _choice_key(remote, series.id), _imdb_url(remote), series
        )

    def _remote_search_results(self, parsed: ParsedRelease) -> list[RemoteSeries]:
        try:
            search_name = re.sub(r"[._]+", " ", parsed.series_title).strip()
            if parsed.year is not None:
                search_name = re.sub(
                    rf"\s*\(?{parsed.year}\)?\s*$", "", search_name
                ).strip()
            return self.jellyfin.search_series(
                search_name, parsed.year, parsed.imdb_id
            )
        except JellyfinError as exc:
            raise ImportBlocked(f"Jellyfin-Metadatensuche fehlgeschlagen: {exc}") from exc

    def _remote_candidates(
        self, parsed: ParsedRelease, *, results: list[RemoteSeries] | None = None
    ) -> list[RemoteSeries]:
        if results is None:
            results = self._remote_search_results(parsed)
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
            _choice_key(item): item for item in candidates
        }
        return list(identities.values())

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
        target = _contained_path(self.config.shows_dir, season_path / unit.path.name)
        source_relative = unit.path.relative_to(self.config.income_dir).as_posix()
        _recover_incomplete_target(target)
        if target.exists():
            raise ImportBlocked("Ein gleichnamiges Ziel existiert bereits")
        try:
            _ensure_directory(series_path)
            _ensure_directory(season_path)
            filesystem.check_pair(unit.path, season_path)
            with (
                filesystem.open_path(unit.path.parent) as source_parent,
                filesystem.open_path(season_path) as target_parent,
                filesystem.open_path(unit.path) as source_fd,
            ):
                expected = filesystem.snapshot_fd(source_fd, sync=True)
                if _signature(unit.path) != unit.signature:
                    raise ImportBlocked("Quelle hat sich vor dem Verschieben verändert")
                parsed = self._parse_source(unit)
                if parsed is None:
                    raise ImportBlocked("Quelle ist vor dem Verschieben nicht mehr lesbar zugeordnet")
                operation_id = uuid.uuid4().hex
                self.storage.prepare_media_move(
                    operation_id, source_relative,
                    target.relative_to(self.config.shows_dir.resolve()).as_posix(),
                    expected,
                    {"parsed_title": parsed.series_title, "season": parsed.season,
                     "episode": parsed.episode},
                )
                moved = False
                try:
                    # The namespace change must not precede its durable intent.
                    _fsync_directory(series_path.parent)
                    _fsync_directory(series_path)
                    os.fsync(source_parent)
                    os.fsync(target_parent)
                    current = os.stat(
                        unit.path.name, dir_fd=source_parent, follow_symlinks=False
                    )
                    if (current.st_dev, current.st_ino) != (expected["."][0], expected["."][2]):
                        raise ImportBlocked("Quellidentität hat sich vor dem Verschieben verändert")
                    if _signature(unit.path) != unit.signature:
                        raise ImportBlocked("Quelle hat sich vor dem Verschieben verändert")
                    filesystem.rename_noreplace(
                        source_parent, unit.path.name, target_parent, target.name
                    )
                    moved = True
                    if filesystem.snapshot(target) != expected:
                        raise ImportBlocked("Identität am Ziel stimmt nach dem Verschieben nicht überein")
                    _fsync_directory(target.parent)
                    _fsync_directory(unit.path.parent)
                    self.storage.complete_media_move(operation_id)
                except Exception as exc:
                    # A rename can have succeeded even if a later step failed.
                    if moved or not unit.path.exists():
                        self.storage.set_library_refresh_pending(True)
                        raise ImportBlocked(
                            f"Bereits verschoben nach {target}. Abschluss noch offen: {exc}"
                        ) from exc
                    self.storage.cancel_media_move(operation_id)
                    raise
        except filesystem.FilesystemBlocked as exc:
            raise ImportBlocked(str(exc)) from exc
        return target, None

    def recover_moves(self) -> set[str]:
        pending = self.storage.pending_media_moves()
        blocked = {row["source_path"] for row in pending}
        if not pending:
            return blocked
        self._validate_mounts()
        for row in self.storage.pending_media_moves():
            if row["state"] == "manual":
                continue
            try:
                source = _contained_path(self.config.income_dir, self.config.income_dir / row["source_path"])
                target = _contained_path(self.config.shows_dir, self.config.shows_dir / row["target_path"])
                expected = json.loads(row["identity_json"])
                if source.exists():
                    if filesystem.snapshot(source) != expected:
                        raise ImportBlocked("Quellidentität des offenen Vorgangs ist widersprüchlich")
                    if target.exists() and filesystem.snapshot(target) == expected:
                        raise ImportBlocked("Quelle und Ziel des offenen Vorgangs sind gleichzeitig vorhanden")
                    self.storage.cancel_media_move(row["operation_id"])
                    blocked.discard(row["source_path"])
                    continue
                if not target.exists() or filesystem.snapshot(target) != expected:
                    raise ImportBlocked("Erwartete Datei des offenen Vorgangs ist nicht eindeutig vorhanden")
                if filesystem.snapshot(target, sync=True) != expected:
                    raise ImportBlocked("Ziel hat sich während des Abschlusses verändert")
                _fsync_directory(target.parent)
                _fsync_directory(source.parent)
                self.storage.complete_media_move(row["operation_id"])
                blocked.discard(row["source_path"])
            except (ImportBlocked, filesystem.FilesystemBlocked, ValueError, KeyError, TypeError) as exc:
                self.storage.block_media_move(
                    row["operation_id"], f"Offene Verschiebung muss manuell geprüft werden: {exc}"
                )
            except OSError as exc:
                self.storage.update_media_import(
                    row["source_path"], "blocked",
                    f"Abschluss der Verschiebung noch offen: {exc}",
                    target_path=row["target_path"],
                )
        return blocked

    @staticmethod
    def _best_effort_signature(path: Path) -> str:
        try:
            return _signature(path)
        except (OSError, ImportBlocked):
            return "unreadable"


class ImportBlocked(RuntimeError):
    pass


class ImportSelectionRequired(ImportBlocked):
    pass


class ImportWaiting(ImportBlocked):
    pass


def _provider_id(series: RemoteSeries, provider: str) -> str | None:
    return next(
        (value for key, value in series.provider_ids if key.casefold() == provider),
        None,
    )


def _imdb_url(series: RemoteSeries) -> str | None:
    imdb_id = _provider_id(series, "imdb")
    if imdb_id and re.fullmatch(r"tt\d{7,10}", imdb_id, re.IGNORECASE):
        return f"https://www.imdb.com/title/{imdb_id.lower()}/"
    return None


def _choice_key(series: RemoteSeries, existing_series_id: str | None = None) -> str:
    identity = [
        normalize_title(series.name),
        series.production_year,
        sorted((key.casefold(), value.casefold()) for key, value in series.provider_ids),
    ]
    if existing_series_id is not None:
        identity.append(existing_series_id)
    payload = json.dumps(
        identity,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    with filesystem.open_path(path) as descriptor:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ImportBlocked("Zu synchronisierender Pfad ist kein Verzeichnis")
        os.fsync(descriptor)


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
