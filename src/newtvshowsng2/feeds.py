from __future__ import annotations

import logging

import feedparser
import requests

from .models import FeedRelease
from .parsing import feed_entry_to_release

LOGGER = logging.getLogger(__name__)


class FeedError(RuntimeError):
    pass


class FeedClient:
    def __init__(
        self, timeout: float = 20.0, session: requests.Session | None = None
    ) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "NewTVShowsNG2/1.0 (+RSS reader; read-only)"}
        )

    def load(self, feed_url: str) -> list[FeedRelease]:
        try:
            response = self.session.get(feed_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FeedError(f"Abruf fehlgeschlagen: {exc}") from exc

        parsed = feedparser.parse(response.content)
        entries = getattr(parsed, "entries", [])
        if getattr(parsed, "bozo", False) and not entries:
            error = getattr(parsed, "bozo_exception", "ungültiger Feed")
            raise FeedError(f"Feed konnte nicht gelesen werden: {error}")

        releases = [feed_entry_to_release(feed_url, entry) for entry in entries]
        result = [release for release in releases if release is not None]
        LOGGER.info("RSS %s: %d Einträge geladen", feed_url, len(result))
        return result
