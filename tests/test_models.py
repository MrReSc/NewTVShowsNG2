from newtvshowsng2.models import Library, Series


def test_library_tracks_exact_and_highest_episodes() -> None:
    library = Library([Series("show", "Show")])
    library.add_episode("show", 3, 2)
    library.add_episode("show", 3, 6)

    assert library.episode_exists("show", 3, 2)
    assert not library.episode_exists("show", 3, 3)
    assert library.episode_in_season("show", 3) == 6
    assert library.season_is_current("show", 3)

    library.add_episode("show", 4, 1)
    assert not library.season_is_current("show", 3)
