from newtvshowsng2.matching import match_release
from newtvshowsng2.models import Series
from newtvshowsng2.parsing import parse_release

SERIES = [
    Series("twd", "The Walking Dead", imdb_id="tt1520211"),
    Series(
        "dead-city",
        "The Walking Dead: Dead City",
        production_year=2023,
        imdb_id="tt18546730",
    ),
]


def parsed(title: str, content: str = ""):
    result = parse_release(title, content)
    assert result is not None
    return result


def test_spinoff_matches_full_title_not_shorter_parent() -> None:
    match = match_release(parsed("The.Walking.Dead.Dead.City.S03.German"), SERIES)

    assert match is not None
    assert match.series.id == "dead-city"
    assert match.method == "Titel"
    assert not match.warning


def test_parent_title_matches_parent() -> None:
    match = match_release(parsed("The.Walking.Dead.S03.German"), SERIES)

    assert match is not None
    assert match.series.id == "twd"


def test_missing_first_character_is_marked_for_review() -> None:
    match = match_release(parsed("he.Walking.Dead.Dead.City.S03.German"), SERIES)

    assert match is not None
    assert match.series.id == "dead-city"
    assert match.warning
    assert match.method == "Ähnlicher Titel"


def test_imdb_id_wins() -> None:
    match = match_release(
        parsed("Completely.Wrong.S03", "image tt18546730-SHD.jpg"), SERIES
    )

    assert match is not None
    assert match.series.id == "dead-city"
    assert match.method == "IMDb-ID"


def test_imdb_id_matching_is_case_insensitive() -> None:
    items = [Series("one", "Some Show", imdb_id="TT18546730")]

    match = match_release(parsed("Wrong.Title.S01E01", "tt18546730"), items)

    assert match is not None
    assert match.series.id == "one"


def test_conflicting_imdb_id_prevents_title_fallback() -> None:
    match = match_release(
        parsed("The.Walking.Dead.S03", "image tt9999999-SHD.jpg"), SERIES
    )

    assert match is None


def test_unrelated_show_does_not_match() -> None:
    assert match_release(parsed("The.Walking.S03"), SERIES) is None


def test_original_title_is_used() -> None:
    items = [Series("one", "Deutscher Titel", original_title="Original Show")]
    match = match_release(parsed("Original.Show.S01"), items)

    assert match is not None
    assert match.method == "Originaltitel"


def test_explicit_conflicting_year_is_unsafe() -> None:
    items = [Series("new", "Doctor Who", production_year=2023)]
    match = match_release(parsed("Doctor.Who.2005.S01E01"), items)

    assert match is not None
    assert match.warning


def test_year_can_be_part_of_the_actual_show_title() -> None:
    items = [Series("davos", "Davos 1917", production_year=2023)]
    match = match_release(parsed("Davos.1917.S01E01"), items)

    assert match is not None
    assert match.series.id == "davos"
    assert match.method == "Titel"
    assert not match.warning
