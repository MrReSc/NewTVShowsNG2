import pytest

from newtvshowsng2.jellyfin import JellyfinClient, JellyfinError


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class Session:
    def __init__(self, version="12.0.0"):
        self.headers = {}
        self.version = version
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if url.endswith("/System/Info/Public"):
            return Response({"Version": self.version})
        if url.endswith("/Library/VirtualFolders"):
            return Response(
                [
                    {
                        "CollectionType": "tvshows",
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
            return Response(
                {
                    "Items": [
                        {
                            "ParentIndexNumber": 3,
                            "IndexNumber": 1,
                            "IndexNumberEnd": 2,
                            "LocationType": "FileSystem",
                        },
                        {
                            "ParentIndexNumber": 3,
                            "IndexNumber": 3,
                            "LocationType": "Virtual",
                            "PremiereDate": "2099-01-01T00:00:00Z",
                        },
                    ],
                    "TotalRecordCount": 2,
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


def test_loads_jellyfin_12_with_modern_authorization() -> None:
    session = Session()
    client = JellyfinClient("http://jellyfin.test/base", "secret", session=session)

    library = client.load_library()

    assert library.series[0].imdb_id == "tt18546730"
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


def test_loads_complete_season_inventory_and_combined_episodes() -> None:
    client = JellyfinClient("http://jellyfin.test", "secret", session=Session())

    assert client.load_season_episodes("series-1", 3) == {1, 2, 3}


def test_ignores_specials_displayed_with_regular_season() -> None:
    session = Session()
    original_get = session.get

    def get(url, params=None, timeout=None):
        if "/Shows/" in url and url.endswith("/Episodes"):
            return Response(
                {
                    "Items": [
                        {"ParentIndexNumber": 3, "IndexNumber": 1},
                        {"ParentIndexNumber": 3, "IndexNumber": 2},
                        {"ParentIndexNumber": 0, "IndexNumber": 7},
                    ]
                }
            )
        return original_get(url, params, timeout)

    session.get = get
    client = JellyfinClient("http://jellyfin.test", "secret", session=session)

    assert client.load_season_episodes("series-1", 3) == {1, 2}


def test_rejects_episode_from_another_regular_season() -> None:
    session = Session()
    original_get = session.get

    def get(url, params=None, timeout=None):
        if "/Shows/" in url and url.endswith("/Episodes"):
            return Response(
                {"Items": [{"ParentIndexNumber": 2, "IndexNumber": 1}]}
            )
        return original_get(url, params, timeout)

    session.get = get
    client = JellyfinClient("http://jellyfin.test", "secret", session=session)

    with pytest.raises(JellyfinError, match="Episode aus Staffel 2"):
        client.load_season_episodes("series-1", 3)


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
        "http://jellyfin.test", "secret", session=session
    ).load_library()

    assert not library.missing_episode_tracking_enabled


def test_rejects_non_v12_server() -> None:
    client = JellyfinClient(
        "http://jellyfin.test", "secret", session=Session("10.11.11")
    )

    with pytest.raises(JellyfinError, match="benötigt wird 12.x"):
        client.load_library()
