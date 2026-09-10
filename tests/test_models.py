from newtvshowsng2.models import Library, Series


def test_library_tracks_exact_and_highest_episodes() -> None:
    library = Library([Series("show", "Show")])
    library.add_episode("show", 3, 2)
    library.add_episode("show", 3, 6)

    assert library.episode_exists("show", 3, 2)
    assert not library.episode_exists("show", 3, 3)
    assert library.episode_in_season("show", 3) == 6
    assert library.season_counts("show", 3) == (2, None)
    assert library.season_is_complete("show", 3) is None

    library.set_expected_episodes("show", 3, {1, 2, 3, 4, 5, 6})
    assert library.season_counts("show", 3) == (2, 6)
    assert not library.season_is_complete("show", 3)

    for episode in (1, 3, 4, 5):
        library.add_episode("show", 3, episode)
    assert library.season_is_complete("show", 3)
