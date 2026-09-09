from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Series:
    id: str
    name: str
    original_title: str | None = None
    production_year: int | None = None
    imdb_id: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedRelease:
    raw_title: str
    series_title: str
    normalized_title: str
    year: int | None
    season: int
    episode: int | None
    imdb_id: str | None


@dataclass(frozen=True, slots=True)
class FeedRelease:
    feed_url: str
    guid: str | None
    link: str
    title: str
    published_at: datetime
    content: str = ""


@dataclass(frozen=True, slots=True)
class Match:
    series: Series
    method: str
    warning: bool = False


@dataclass(slots=True)
class Library:
    series: list[Series]
    episodes: set[tuple[str, int, int]] = field(default_factory=set)
    highest_episode: dict[tuple[str, int], int] = field(default_factory=dict)
    highest_season: dict[str, int] = field(default_factory=dict)

    def add_episode(self, series_id: str, season: int, episode: int) -> None:
        self.episodes.add((series_id, season, episode))
        season_key = (series_id, season)
        self.highest_episode[season_key] = max(
            episode, self.highest_episode.get(season_key, -1)
        )
        self.highest_season[series_id] = max(
            season, self.highest_season.get(series_id, -1)
        )

    def episode_exists(self, series_id: str, season: int, episode: int) -> bool:
        return (series_id, season, episode) in self.episodes

    def episode_in_season(self, series_id: str, season: int) -> int | None:
        value = self.highest_episode.get((series_id, season))
        return value if value is not None and value >= 0 else None

    def season_is_current(self, series_id: str, season: int) -> bool:
        return season >= self.highest_season.get(series_id, -1)
