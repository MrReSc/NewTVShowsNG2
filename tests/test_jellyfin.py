import pytest
import requests
import json

from newtvshowsng2.jellyfin import JellyfinClient, JellyfinError


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status
        self.content = json.dumps(payload).encode() if payload is not None else b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class Session:
    def __init__(self, version="12.0.0"):
        self.headers = {}
        self.version = version
        self.calls = []
        self.users = [
            {
                "Id": "user-1",
                "Name": "Hans",
                "Policy": {"IsDisabled": False},
                "Configuration": {"DisplayMissingEpisodes": False},
            }
        ]
        self.episode_items = [
            {
                "ParentIndexNumber": 3,
                "IndexNumber": 1,
                "IndexNumberEnd": 2,
                "LocationType": "FileSystem",
                "UserData": {"Played": True},
            },
            {
                "ParentIndexNumber": 3,
                "IndexNumber": 3,
                "LocationType": "Virtual",
                "PremiereDate": "2099-01-01T00:00:00Z",
                "UserData": {"Played": False},
            },
        ]
        self.post_calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if url.endswith("/System/Info/Public"):
            return Response({"Version": self.version})
        if url.endswith("/Users"):
            return Response(self.users)
        if url.endswith("/Library/VirtualFolders"):
            return Response(
                [
                    {
                        "CollectionType": "tvshows",
                        "Locations": ["/media/tv"],
                        "LibraryOptions": {
                            "TypeOptions": [
                                {
                                    "Type": "Series",
                                    "MetadataFetchers": ["Missing Episode Fetcher"],
                                }
                            ]
                        },
                    }
                ]
            )
        if "/Shows/" in url and url.endswith("/Episodes"):
            # Reproduce Jellyfin's hidden virtual seasons with DisplayMissingEpisodes=false.
            if "season" in params:
                return Response({"Items": [], "TotalRecordCount": 0})
            start, limit = int(params["startIndex"]), int(params["limit"])
            return Response(
                {
                    "Items": self.episode_items[start : start + limit],
                    "TotalRecordCount": len(self.episode_items),
                }
            )
        if params["includeItemTypes"] == "Series":
            return Response(
                {
                    "Items": [
                        {
                            "Id": "series-1",
                            "Name": "The Walking Dead: Dead City",
                            "OriginalTitle": "The Walking Dead: Dead City",
                            "ProductionYear": 2023,
                            "ProviderIds": {"Imdb": "tt18546730"},
                            "Path": "/media/tv/The Walking Dead Dead City (2023)",
                        }
                    ],
                    "TotalRecordCount": 1,
                }
            )
        return Response(
            {
                "Items": [
                    {
                        "SeriesId": "series-1",
                        "ParentIndexNumber": 3,
                        "IndexNumber": 6,
                        "IndexNumberEnd": 7,
                    }
                ],
                "TotalRecordCount": 1,
            }
        )

    def post(self, url, json=None, timeout=None):
        self.post_calls.append((url, json, timeout))
        if url.endswith("/Items/RemoteSearch/Series"):
            return Response(
                [
                    {
                        "Name": "Neue Serie",
                        "ProductionYear": 2026,
                        "ProviderIds": {"Tvdb": "1234"},
                    }
                ]
            )
        return Response(None)


def test_loads_jellyfin_12_with_modern_authorization() -> None:
    session = Session()
    client = JellyfinClient(
        "http://jellyfin.test/base", "secret", "hans", session=session
    )

    library = client.load_library()

    assert library.series[0].imdb_id == "tt18546730"
    assert library.series[0].path == "/media/tv/The Walking Dead Dead City (2023)"
    assert library.episode_in_season("series-1", 3) == 7
    assert library.missing_episode_tracking_enabled
    assert session.headers["Authorization"].startswith("MediaBrowser ")
    assert 'Token="secret"' in session.headers["Authorization"]
    assert all("api_key" not in (params or {}) for _, params, _ in session.calls)
    assert any(url.endswith("/Items") for url, _, _ in session.calls)
    episode_params = next(
        params
        for url, params, _ in session.calls
        if url.endswith("/Items") and params["includeItemTypes"] == "Episode"
    )
    assert episode_params["isMissing"] == "false"
    assert episode_params["locationTypes"] == "FileSystem"


def test_library_paths_remote_search_and_refresh() -> None:
    session = Session()
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)

    assert client.tv_library_locations() == ("/media/tv",)
    results = client.search_series("Neue Serie", 2026)
    client.refresh_library()

    assert results[0].name == "Neue Serie"
    assert results[0].provider_ids == (("Tvdb", "1234"),)
    assert session.post_calls[0][0].endswith("/Items/RemoteSearch/Series")
    assert session.post_calls[0][1]["SearchInfo"]["Year"] == 2026
    assert session.post_calls[1][0].endswith("/Library/Refresh")


def test_loads_complete_season_inventory_and_combined_episodes() -> None:
    session = Session()
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    inventory = client.load_series_episodes("series-1")[3]
    assert inventory.episodes == {1, 2, 3}
    assert inventory.played == {1, 2}
    params = session.calls[-1][1]
    assert params["userId"] == "user-1"
    assert params["enableUserData"] == "true"
    assert "season" not in params and "seasonId" not in params


def test_groups_specials_and_other_seasons_separately() -> None:
    session = Session()
    session.episode_items += [
        {"ParentIndexNumber": 0, "IndexNumber": 7, "UserData": {"Played": True}},
        {"ParentIndexNumber": 4, "IndexNumber": 1, "UserData": {"Played": False}},
    ]
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    seasons = client.load_series_episodes("series-1")
    assert seasons[3].episodes == {1, 2, 3}
    assert seasons[0].episodes == seasons[0].played == {7}
    assert seasons[4].episodes == {1}


def test_missing_episode_tracking_must_be_enabled() -> None:
    session = Session()
    original_get = session.get

    def get(url, params=None, timeout=None):
        if url.endswith("/Library/VirtualFolders"):
            return Response(
                [
                    {
                        "CollectionType": "tvshows",
                        "LibraryOptions": {"TypeOptions": []},
                    }
                ]
            )
        return original_get(url, params, timeout)

    session.get = get
    library = JellyfinClient(
        "http://jellyfin.test", "secret", "Hans", session=session
    ).load_library()

    assert not library.missing_episode_tracking_enabled


def test_rejects_non_v12_server() -> None:
    client = JellyfinClient(
        "http://jellyfin.test", "secret", "Hans", session=Session("10.11.11")
    )

    with pytest.raises(JellyfinError, match="benötigt wird 12.x"):
        client.load_library()


@pytest.mark.parametrize(
    "users",
    [
        [],
        [{"Name": "Other", "Id": "other"}],
        [{"Name": "Hans", "Id": "one"}, {"Name": "HANS", "Id": "two"}],
        [{"Name": "Hans", "Id": "one", "Policy": {"IsDisabled": True}}],
        [{"Name": "Hans"}],
        {},
    ],
)
def test_rejects_invalid_or_ambiguous_user(users):
    session = Session()
    session.users = users
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    with pytest.raises(JellyfinError):
        client.load_library()
    assert client.user_id is None
    assert not any(url.endswith("/Items") for url, _, _ in session.calls)


def test_resolves_user_fresh_on_every_scan():
    session = Session()
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    session.users[0]["Policy"]["IsDisabled"] = True
    with pytest.raises(JellyfinError, match="deaktiviert"):
        client.load_library()
    assert client.user_id is None
    assert sum(url.endswith("/Users") for url, _, _ in session.calls) == 2


def test_pages_and_deduplicates_episode_ranges():
    session = Session()
    session.episode_items = [
        {
            "ParentIndexNumber": 5,
            "IndexNumber": 1,
            "IndexNumberEnd": 2,
            "UserData": {"Played": True},
        }
    ] * 500 + [
        {"ParentIndexNumber": 5, "IndexNumber": 3, "UserData": {"Played": False}}
    ]
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    seasons = client.load_series_episodes("series-1")
    assert seasons[5].episodes == {1, 2, 3}
    assert seasons[5].played == {1, 2}
    assert [
        params["startIndex"]
        for url, params, _ in session.calls
        if url.endswith("/Episodes")
    ] == ["0", "500"]


def test_only_explicit_played_true_counts():
    session = Session()
    session.episode_items = [
        {"parentIndexNumber": 5, "indexNumber": 1, "userData": {"played": True}},
        {
            "ParentIndexNumber": 5,
            "IndexNumber": 2,
            "UserData": {
                "Played": False,
                "PlayCount": 1,
                "LastPlayedDate": "2026-07-04T18:10:14Z",
            },
        },
        {"ParentIndexNumber": 5, "IndexNumber": 3},
        {"ParentIndexNumber": 5, "IndexNumber": 4, "UserData": {"Played": "true"}},
    ]
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    inventory = client.load_series_episodes("series-1")[5]
    assert inventory.played == {1}
    assert inventory.episodes == {1, 2, 3, 4}
    assert not inventory.played_status_complete


@pytest.mark.parametrize(
    "item",
    [
        {"IndexNumber": 1},
        {"ParentIndexNumber": 5},
        {"ParentIndexNumber": 5, "IndexNumber": 3, "IndexNumberEnd": 1},
    ],
)
def test_rejects_malformed_episode_inventory(item):
    session = Session()
    session.episode_items = [item]
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    with pytest.raises(JellyfinError):
        client.load_series_episodes("series-1")


def test_http_failure_does_not_return_partial_inventory():
    session = Session()
    original = session.get

    def get(url, params=None, timeout=None):
        if url.endswith("/Episodes"):
            if params["startIndex"] == "0":
                return Response(
                    {
                        "Items": [
                            {
                                "ParentIndexNumber": 5,
                                "IndexNumber": 1,
                                "UserData": {"Played": True},
                            }
                        ],
                        "TotalRecordCount": 2,
                    }
                )
            return Response({}, status=500)
        return original(url, params=params, timeout=timeout)

    session.get = get
    client = JellyfinClient("http://jellyfin.test", "secret", "Hans", session=session)
    client.load_library()
    with pytest.raises(JellyfinError, match="fehlgeschlagen"):
        client.load_series_episodes("series-1")
