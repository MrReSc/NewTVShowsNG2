from __future__ import annotations

from collections.abc import Iterable

from .models import Match, ParsedRelease, Series
from .parsing import normalize_title


def match_release(
    release: ParsedRelease, series_items: Iterable[Series]
) -> Match | None:
    series = list(series_items)

    if release.imdb_id:
        id_matches = [item for item in series if item.imdb_id == release.imdb_id]
        if id_matches:
            return Match(
                _select_by_year(id_matches, release.year),
                "IMDb-ID",
                len(id_matches) > 1,
            )

    candidates = [
        item
        for item in series
        if not (
            release.imdb_id
            and item.imdb_id
            and release.imdb_id.casefold() != item.imdb_id.casefold()
        )
    ]

    name_exact = [
        item
        for item in candidates
        if normalize_title(item.name) == release.normalized_title
    ]
    if name_exact:
        selected = _select_by_year(name_exact, release.year)
        return Match(selected, "Titel", _is_ambiguous(name_exact, release.year))

    original_exact = [
        item
        for item in candidates
        if item.original_title
        and normalize_title(item.original_title) == release.normalized_title
    ]
    if original_exact:
        selected = _select_by_year(original_exact, release.year)
        return Match(
            selected, "Originaltitel", _is_ambiguous(original_exact, release.year)
        )

    fuzzy: list[tuple[int, Series]] = []
    for item in candidates:
        distances = [
            _guarded_distance(release.normalized_title, normalize_title(item.name))
        ]
        if item.original_title:
            distances.append(
                _guarded_distance(
                    release.normalized_title, normalize_title(item.original_title)
                )
            )
        valid = [distance for distance in distances if distance is not None]
        if valid:
            fuzzy.append((min(valid), item))

    if not fuzzy:
        return None
    fuzzy.sort(
        key=lambda value: (
            value[0],
            _year_distance(value[1], release.year),
            value[1].id,
        )
    )
    _, selected = fuzzy[0]
    return Match(selected, "Ähnlicher Titel", True)


def _guarded_distance(left: str, right: str) -> int | None:
    if not left or not right:
        return None
    left_tokens = left.split()
    right_tokens = right.split()
    if abs(len(left_tokens) - len(right_tokens)) > 1:
        return None
    max_length = max(len(left), len(right))
    if abs(len(left) - len(right)) > max(2, round(max_length * 0.10)):
        return None
    distance = _edit_distance(left, right)
    return distance if distance <= max(1, round(max_length * 0.08)) else None


def _edit_distance(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _select_by_year(items: list[Series], year: int | None) -> Series:
    if year is not None:
        exact = [item for item in items if item.production_year == year]
        if exact:
            return min(exact, key=lambda item: item.id)
    return min(items, key=lambda item: (-(item.production_year or 0), item.id))


def _is_ambiguous(items: list[Series], year: int | None) -> bool:
    if len(items) <= 1:
        return False
    return not (
        year is not None and sum(item.production_year == year for item in items) == 1
    )


def _year_distance(item: Series, year: int | None) -> int:
    if year is None or item.production_year is None:
        return 9999
    return abs(item.production_year - year)
