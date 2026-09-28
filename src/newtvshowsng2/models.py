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
    path: str | None = None
    provider_ids: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class RemoteSeries:
    name: str
    production_year: int | None
    provider_ids: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ParsedRelease:
    raw_title: str
    series_title: str
    normalized_title: str
    year: int | None
    season: int
    season_end: int
    episode: int | None
    imdb_id: str | None

    @property
    def seasons(self) -> range:
        return range(self.season, self.season_end + 1)


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
class SeasonInventory:
    episodes: set[int] = field(default_factory=set)
    played: set[int] = field(default_factory=set)
    played_status_complete: bool = True


@dataclass(slots=True)
class Library:
    series: list[Series]
    episodes: set[tuple[str, int, int]] = field(default_factory=set)
    episodes_by_season: dict[tuple[str, int], set[int]] = field(default_factory=dict)
    expected_episodes: dict[tuple[str, int], set[int]] = field(default_factory=dict)
    highest_episode: dict[tuple[str, int], int] = field(default_factory=dict)
    missing_episode_tracking_enabled: bool = False
    played_by_season: dict[tuple[str, int], set[int]] = field(default_factory=dict)
    played_counts_known: set[tuple[str, int]] = field(default_factory=set)

    def add_episode(self, series_id: str, season: int, episode: int) -> None:
        self.episodes.add((series_id, season, episode))
        season_key = (series_id, season)
        self.episodes_by_season.setdefault(season_key, set()).add(episode)
        self.highest_episode[season_key] = max(
            episode, self.highest_episode.get(season_key, -1)
        )

    def episode_exists(self, series_id: str, season: int, episode: int) -> bool:
        return (series_id, season, episode) in self.episodes

    def episode_numbers(self, series_id: str, season: int) -> set[int]:
        return set(self.episodes_by_season.get((series_id, season), set()))

    def set_expected_episodes(
        self, series_id: str, season: int, episodes: set[int]
    ) -> None:
        key = (series_id, season)
        if episodes:
            self.expected_episodes[key] = set(episodes)
        else:
            self.expected_episodes.pop(key, None)

    def set_played_episodes(
        self, series_id: str, season: int, episodes: set[int], *, complete: bool
    ) -> None:
        key = (series_id, season)
        self.played_by_season[key] = set(episodes)
        self.played_counts_known.discard(key)
        if complete:
            self.played_counts_known.add(key)

    def played_numbers(self, series_id: str, season: int) -> set[int]:
        return set(self.played_by_season.get((series_id, season), set()))

    def played_count(self, series_id: str, season: int) -> int | None:
        if (series_id, season) not in self.played_counts_known:
            return None
        return len(self.played_numbers(series_id, season))

    def season_counts(self, series_id: str, season: int) -> tuple[int, int | None]:
        available = len(self.episode_numbers(series_id, season))
        expected = self.expected_episodes.get((series_id, season))
        return available, len(expected) if expected is not None else None

    def season_is_complete(self, series_id: str, season: int) -> bool | None:
        expected = self.expected_episodes.get((series_id, season))
        if expected is None:
            return None
        return expected.issubset(self.episode_numbers(series_id, season))

    def episode_in_season(self, series_id: str, season: int) -> int | None:
        value = self.highest_episode.get((series_id, season))
        return value if value is not None and value >= 0 else None
