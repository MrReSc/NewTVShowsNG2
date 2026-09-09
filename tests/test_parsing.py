from datetime import UTC

from newtvshowsng2.parsing import feed_entry_to_release, normalize_title, parse_release


def test_parse_season_release_and_imdb_id() -> None:
    parsed = parse_release(
        "The.Walking.Dead.Dead.City.S03.German.DL.720P.WEB.X264-WAYNE",
        '<img src="https://example.test/images/tt18546730-SHD.jpg">',
    )

    assert parsed is not None
    assert parsed.series_title == "The.Walking.Dead.Dead.City"
    assert parsed.normalized_title == "the walking dead dead city"
    assert parsed.season == 3
    assert parsed.episode is None
    assert parsed.imdb_id == "tt18546730"


def test_parse_episode_and_year() -> None:
    parsed = parse_release("A.Show.(2024).S001E123.German")

    assert parsed is not None
    assert parsed.normalized_title == "a show"
    assert parsed.year == 2024
    assert parsed.season == 1
    assert parsed.episode == 123


def test_parse_complete_and_german_characters() -> None:
    parsed = parse_release(
        "Storage.Wars.-.Die.Geschaeftemacher.S01.COMPLETE.GERMAN.DOKU"
    )

    assert parsed is not None
    assert parsed.normalized_title == "storage wars die geschaeftemacher"
    assert (
        normalize_title("Storage Wars – Die Geschäftemacher") == parsed.normalized_title
    )


def test_reject_title_without_supported_marker() -> None:
    assert parse_release("Some.Show.1x02.German") is None


def test_feed_entry_uses_updated_date_and_collects_content() -> None:
    release = feed_entry_to_release(
        "https://feed.test/rss",
        {
            "title": "Show.S01",
            "link": "https://feed.test/show",
            "id": "item-1",
            "updated_parsed": (2026, 9, 8, 18, 0, 0, 1, 251, 0),
            "content": [{"value": "tt1234567"}],
        },
    )

    assert release is not None
    assert release.guid == "item-1"
    assert release.published_at.tzinfo == UTC
    assert release.content == "tt1234567"


def test_feed_entry_rejects_unsafe_link() -> None:
    assert (
        feed_entry_to_release(
            "https://feed.test/rss",
            {"title": "Show.S01", "link": "javascript:alert(1)"},
        )
        is None
    )
