from __future__ import annotations

import logging
from typing import Any

import requests

from . import __version__
from .models import Library, Series

LOGGER = logging.getLogger(__name__)


class JellyfinError(RuntimeError):
    pass


class JellyfinClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": (
                    'MediaBrowser Client="NewTVShowsNG2", '
                    'Device="Docker", DeviceId="newtvshowsng2", '
                    f'Version="{__version__}", Token="{api_key}"'
                ),
            }
        )

    def load_library(self) -> Library:
        version = self._server_version()
        if version.split(".", 1)[0] != "12":
            raise JellyfinError(
                f"Nicht unterstützte Jellyfin-Version {version!r}; benötigt wird 12.x"
            )

        series_items = self._get_all_items(
            {
                "includeItemTypes": "Series",
                "recursive": "true",
                "fields": "OriginalTitle,ProviderIds",
                "enableImages": "false",
                "enableUserData": "false",
            }
        )
        series = [self._to_series(item) for item in series_items]
        series = [item for item in series if item is not None]
        library = Library(
            series=series,
            missing_episode_tracking_enabled=self._missing_episode_tracking_enabled(),
        )

        valid_series_ids = {item.id for item in series}
        episode_items = self._get_all_items(
            {
                "includeItemTypes": "Episode",
                "recursive": "true",
                "isMissing": "false",
                "locationTypes": "FileSystem",
                "enableImages": "false",
                "enableUserData": "false",
            }
        )
        for item in episode_items:
            series_id = _field(item, "SeriesId")
            season = _as_int(_field(item, "ParentIndexNumber"))
            first_episode = _as_int(_field(item, "IndexNumber"))
            if (
                series_id in valid_series_ids
                and season is not None
                and first_episode is not None
            ):
                last_episode = _as_int(_field(item, "IndexNumberEnd"))
                if last_episode is None or last_episode < first_episode:
                    last_episode = first_episode
                for episode in range(first_episode, last_episode + 1):
                    library.add_episode(str(series_id), season, episode)

        LOGGER.info(
            "Jellyfin %s: %d Serien und %d Episoden geladen",
            version,
            len(library.series),
            len(library.episodes),
        )
        return library

    def load_season_episodes(self, series_id: str, season: int) -> set[int]:
        payload = self._get_json(
            f"/Shows/{series_id}/Episodes",
            {
                "season": str(season),
                "enableImages": "false",
                "enableUserData": "false",
            },
        )
        items = _field(payload, "Items")
        if not isinstance(items, list):
            raise JellyfinError(
                "Jellyfin Staffelabfrage enthält keine gültige Item-Liste"
            )

        episodes: set[int] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            item_season = _as_int(_field(item, "ParentIndexNumber"))
            if item_season is not None and item_season != season:
                raise JellyfinError(
                    "Jellyfin lieferte eine Episode aus Staffel "
                    f"{item_season} für S{season:02d}"
                )
            first = _as_int(_field(item, "IndexNumber"))
            if first is None or first < 0:
                continue
            last = _as_int(_field(item, "IndexNumberEnd"))
            if last is None:
                last = first
            if last < first:
                raise JellyfinError(
                    f"Jellyfin lieferte einen ungültigen Episodenbereich {first}-{last}"
                )
            episodes.update(range(first, last + 1))
        return episodes

    def _missing_episode_tracking_enabled(self) -> bool:
        try:
            folders = self._get_payload("/Library/VirtualFolders")
        except JellyfinError as exc:
            LOGGER.warning(
                "Jellyfin-Bibliothekskonfiguration konnte nicht geprüft werden: %s",
                exc,
            )
            return False
        if not isinstance(folders, list):
            LOGGER.warning(
                "Jellyfin /Library/VirtualFolders lieferte keine gültige Liste"
            )
            return False

        tv_libraries = [
            item
            for item in folders
            if isinstance(item, dict)
            and str(_field(item, "CollectionType") or "").casefold()
            in {"tvshows", "tv"}
        ]
        return bool(tv_libraries) and all(
            _library_imports_missing_episodes(item) for item in tv_libraries
        )

    def _server_version(self) -> str:
        payload = self._get_json("/System/Info/Public")
        version = _field(payload, "Version")
        if not version:
            raise JellyfinError("Jellyfin meldet keine Serverversion")
        return str(version)

    def _get_all_items(self, params: dict[str, str]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        start_index = 0
        page_size = 500
        while True:
            page_params = {
                **params,
                "startIndex": str(start_index),
                "limit": str(page_size),
                "enableTotalRecordCount": "true",
            }
            payload = self._get_json("/Items", page_params)
            items = _field(payload, "Items") or []
            if not isinstance(items, list):
                raise JellyfinError("Jellyfin /Items enthält keine gültige Item-Liste")
            result.extend(item for item in items if isinstance(item, dict))
            total = _as_int(_field(payload, "TotalRecordCount"))
            start_index += len(items)
            if (
                not items
                or len(items) < page_size
                or (total is not None and start_index >= total)
            ):
                break
        return result

    def _get_payload(self, path: str, params: dict[str, str] | None = None) -> Any:
        try:
            response = self.session.get(
                f"{self.base_url}{path}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise JellyfinError(
                f"Jellyfin-Anfrage {path} fehlgeschlagen: {exc}"
            ) from exc
        return payload

    def _get_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        payload = self._get_payload(path, params)
        if not isinstance(payload, dict):
            raise JellyfinError(f"Jellyfin-Anfrage {path} lieferte kein JSON-Objekt")
        return payload

    @staticmethod
    def _to_series(item: dict[str, Any]) -> Series | None:
        series_id = _field(item, "Id")
        name = _field(item, "Name")
        if not series_id or not name:
            return None
        provider_ids = _field(item, "ProviderIds") or {}
        imdb_id = None
        if isinstance(provider_ids, dict):
            imdb_id = next(
                (
                    str(value).lower()
                    for key, value in provider_ids.items()
                    if key.casefold() == "imdb" and value
                ),
                None,
            )
        return Series(
            id=str(series_id),
            name=str(name),
            original_title=(
                str(_field(item, "OriginalTitle"))
                if _field(item, "OriginalTitle")
                else None
            ),
            production_year=_as_int(_field(item, "ProductionYear")),
            imdb_id=imdb_id,
        )


def _field(mapping: dict[str, Any], pascal_name: str) -> Any:
    camel_name = pascal_name[:1].lower() + pascal_name[1:]
    return mapping.get(pascal_name, mapping.get(camel_name))


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _library_imports_missing_episodes(folder: dict[str, Any]) -> bool:
    options = _field(folder, "LibraryOptions")
    if not isinstance(options, dict):
        return False
    if _field(options, "ImportMissingEpisodes") is True:
        return True

    type_options = _field(options, "TypeOptions") or []
    if not isinstance(type_options, list):
        return False
    for item in type_options:
        if (
            not isinstance(item, dict)
            or str(_field(item, "Type") or "").casefold() != "series"
        ):
            continue
        fetchers = _field(item, "MetadataFetchers") or []
        if isinstance(fetchers, list) and any(
            "missing episode" in str(fetcher).casefold() for fetcher in fetchers
        ):
            return True
    return False
