from __future__ import annotations

import logging
import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from .jellyfin import JellyfinClient, JellyfinError
from .matching import match_release
from .parsing import parse_release

LOGGER = logging.getLogger(__name__)
IMAGE_TTL = 3600
PLACEHOLDER_TTL = 60
PLACEHOLDER = files("newtvshowsng2").joinpath("static/series-placeholder.svg").read_bytes()


@dataclass(frozen=True)
class SeriesImage:
    content: bytes
    content_type: str
    max_age: int


def placeholder_image() -> SeriesImage:
    return SeriesImage(PLACEHOLDER, "image/svg+xml", PLACEHOLDER_TTL)


def series_image_url(row: Mapping[str, Any]) -> str:
    if row.get("kind") == "import":
        title, season = row.get("parsed_title"), row.get("season")
        if title and season is not None:
            return "/series-image?" + urlencode({"title": f"{title}.S{season:02d}"})
    elif not row.get("match_warning"):
        try:
            series_id = UUID(str(row.get("matched_series_id", ""))).hex
        except ValueError:
            pass
        else:
            return "/series-image?" + urlencode({"id": series_id})
    return "/series-placeholder.svg"


class SeriesImageCache:
    def __init__(
        self,
        jellyfin: JellyfinClient,
        *,
        max_entries: int = 128,
        max_bytes: int = 8 * 1024 * 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.jellyfin = jellyfin
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.clock = clock
        self._entries: OrderedDict[tuple[str, str], tuple[float, SeriesImage]] = OrderedDict()
        self._bytes = 0
        # A dedicated client and this lock keep image requests away from scan state.
        self._lock = threading.Lock()

    def get(self, *, series_id: str = "", title: str = "") -> SeriesImage:
        if bool(series_id) == bool(title):
            raise ValueError("Genau eine Bildreferenz ist erforderlich")
        if series_id:
            series_id = UUID(series_id).hex
        elif len(title) > 512 or parse_release(title) is None:
            raise ValueError("Ungültiger Serientitel")
        key = ("id", series_id) if series_id else ("title", title.casefold())
        with self._lock:
            now = self.clock()
            for expired in [key for key, (until, _) in self._entries.items() if until <= now]:
                self._remove(expired)
            if key in self._entries:
                until, image = self._entries[key]
                self._entries.move_to_end(key)
                return SeriesImage(image.content, image.content_type, math.ceil(until - now))
            image = placeholder_image()
            try:
                if title:
                    match = match_release(parse_release(title), self.jellyfin.load_series())
                    series_id = match.series.id if match and not match.warning else ""
                if series_id:
                    result = self.jellyfin.load_primary_image(series_id)
                    if result is not None:
                        image = SeriesImage(*result, IMAGE_TTL)
            except JellyfinError:
                LOGGER.debug("Serienposter vorübergehend nicht verfügbar", exc_info=True)
            if len(image.content) <= self.max_bytes and self.max_entries > 0:
                while self._entries and (
                    len(self._entries) >= self.max_entries
                    or self._bytes + len(image.content) > self.max_bytes
                ):
                    self._remove(next(iter(self._entries)))
                self._entries[key] = (self.clock() + image.max_age, image)
                self._bytes += len(image.content)
            return image

    def _remove(self, key: tuple[str, str]) -> None:
        _, image = self._entries.pop(key)
        self._bytes -= len(image.content)
