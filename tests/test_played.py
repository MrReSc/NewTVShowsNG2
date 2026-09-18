import json
from dataclasses import replace

import pytest
from test_scanner_and_rendering import Feeds, Jellyfin, release, setup

from newtvshowsng2.jellyfin import JellyfinError
from newtvshowsng2.models import Library, SeasonInventory, Series
from newtvshowsng2.scanner import Scanner
from newtvshowsng2.storage import _library_state


def show_release(marker, variant="1080p"):
    return replace(
        release(f"For.All.Mankind.{marker}.German.{variant}-WAYNE"),
        guid=f"{marker}-{variant}",
        link=f"https://feed.test/{marker}-{variant}",
        content="tt7772588",
    )


def test_deleted_s05_variants_and_episodes_follow_fresh_jellyfin_status(tmp_path):
    cfg, storage, renderer = setup(tmp_path)
    show = Series("show", "For All Mankind", imdb_id="tt7772588")
    library = Library([show], missing_episode_tracking_enabled=True)
    expected = {("show", 5): set(range(1, 11))}
    played = {("show", 5): set(range(1, 10))}
    jellyfin = Jellyfin(library, expected, played=played)
    releases = [show_release("S05", q) for q in ("720p", "1080p", "2160p")]
    releases += [show_release(f"S05E{i:02d}") for i in range(1, 11)]
    releases.append(show_release("S06"))
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds(releases))

    assert scanner.run()
    assert jellyfin.series_calls == ["show"]
    rows = storage.announcements()
    assert len(storage.announcements(current_only=True)) == 5  # 3 variants, E10, S06
    for row in rows:
        if row["season"] == 5:
            assert row["jellyfin_episode_count"] == 0
            assert row["jellyfin_played_episode_count"] == 9
            assert row["needed_episodes"] == (
                [10] if row["episode"] in (None, 10) else []
            )
        else:
            assert row["is_current"]
            assert row["jellyfin_expected_episode_count"] is None
    html = cfg.output_path.read_text()
    assert "0 / 10 vorhanden" in html
    assert "9 / 10 gesehen" in html
    assert "Noch benötigt: E10" in html
    assert ">Gesehen</span>" in html
    assert "In Jellyfin" not in html

    # No feed entries: existing history must still be refreshed.
    scanner.feeds = Feeds([])
    played[("show", 5)].add(10)
    assert scanner.run()
    current = storage.announcements(current_only=True)
    assert len(current) == 1 and current[0]["season"] == 6
    assert all(
        row["status_reason"] == "played"
        for row in storage.announcements()
        if row["season"] == 5
    )

    # A restart must not turn stored display snapshots into a watched database.
    played[("show", 5)].remove(10)
    scanner = Scanner(
        cfg, storage, renderer, Jellyfin(library, expected, played=played), Feeds([])
    )
    assert scanner.run()
    assert len(storage.announcements(current_only=True)) == 5

    # API failure must discard previous watched counts and decisions.
    scanner.jellyfin = Jellyfin(library, error=JellyfinError("offline"))
    assert scanner.run()
    assert len(storage.announcements(current_only=True)) == len(releases)
    assert all(
        row["jellyfin_played_episode_count"] is None for row in storage.announcements()
    )
    assert storage.state()["scan_status"] == "warning"


@pytest.mark.parametrize(
    "available,played,reason,needed",
    [
        ({1, 2, 3}, set(), "available", []),
        (set(), {1, 2, 3}, "played", []),
        ({1, 2}, {2, 3}, "covered", []),
        ({1, 2}, {1, 2}, "missing", [3]),
    ],
)
def test_coverage_uses_union_without_double_counting(available, played, reason, needed):
    library = Library([Series("show", "Show")])
    for episode in available:
        library.add_episode("show", 5, episode)
    library.set_expected_episodes("show", 5, {1, 2, 3})
    library.set_played_episodes("show", 5, played, complete=True)
    state = _library_state(library, "show", 5, None)
    assert state.status_reason == reason
    assert state.is_current == (reason == "missing")
    assert state.available_count == len(available)
    assert state.played_count == len(played)
    assert json.loads(state.needed_episodes) == needed


def test_empty_expected_inventory_never_completes_a_season():
    library = Library([Series("show", "Show")])
    library.set_expected_episodes("show", 6, set())
    assert library.season_is_complete("show", 6) is None
    assert _library_state(library, "show", 6, None).is_current
    assert _library_state(library, "show", 6, None).expected_count is None


def test_played_episode_without_missing_import_does_not_complete_season(tmp_path):
    cfg, storage, renderer = setup(tmp_path)
    library = Library([Series("show", "For All Mankind", imdb_id="tt7772588")])
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        Jellyfin(library, {("show", 5): {1}}, played={("show", 5): {1}}),
        Feeds([show_release("S05"), show_release("S05E01")]),
    )
    assert scanner.run()
    rows = {row["episode"]: row for row in storage.announcements()}
    assert rows[None]["is_current"]
    assert rows[None]["jellyfin_expected_episode_count"] is None
    assert not rows[1]["is_current"]
    assert rows[1]["status_reason"] == "played"


def test_partial_user_data_and_removed_series(tmp_path):
    cfg, storage, renderer = setup(tmp_path)
    library = Library(
        [Series("show", "For All Mankind", imdb_id="tt7772588")],
        missing_episode_tracking_enabled=True,
    )
    jellyfin = Jellyfin(library)
    jellyfin.load_series_episodes = lambda _: {5: SeasonInventory({1, 2}, {1}, False)}
    scanner = Scanner(
        cfg,
        storage,
        renderer,
        jellyfin,
        Feeds([show_release("S05"), show_release("S05E01")]),
    )
    assert scanner.run()
    rows = {row["episode"]: row for row in storage.announcements()}
    assert rows[None]["is_current"] and rows[None]["needed_episodes"] == [2]
    assert rows[None]["jellyfin_played_episode_count"] is None
    assert not rows[1]["is_current"]
    assert storage.state()["scan_status"] == "warning"

    scanner.jellyfin = Jellyfin(Library([]))
    scanner.feeds = Feeds([])
    assert scanner.run()
    assert not storage.announcements(current_only=True)
    assert all(row["status_reason"] == "removed" for row in storage.announcements())
    assert "Serie nicht mehr vorhanden" in cfg.output_path.read_text()


def test_invalid_user_is_visible_scan_error(tmp_path):
    cfg, storage, renderer = setup(tmp_path)
    jellyfin = Jellyfin(Library([]))

    def fail():
        raise JellyfinError("Jellyfin-Benutzer 'Hans' ist deaktiviert")

    jellyfin.load_library = fail
    scanner = Scanner(cfg, storage, renderer, jellyfin, Feeds([]))
    assert not scanner.run()
    assert storage.state()["scan_status"] == "error"
    assert "deaktiviert" in cfg.output_path.read_text()
