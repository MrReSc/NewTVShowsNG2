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
    assert library.episode_in_season("series-1", 3) == 6
    assert session.headers["Authorization"].startswith("MediaBrowser ")
    assert 'Token="secret"' in session.headers["Authorization"]
    assert all("api_key" not in (params or {}) for _, params, _ in session.calls)
    assert any(url.endswith("/Items") for url, _, _ in session.calls)
    episode_params = session.calls[-1][1]
    assert episode_params["isMissing"] == "false"
    assert episode_params["locationTypes"] == "FileSystem"


def test_rejects_non_v12_server() -> None:
    client = JellyfinClient(
        "http://jellyfin.test", "secret", session=Session("10.11.11")
    )

    with pytest.raises(JellyfinError, match="benötigt wird 12.x"):
        client.load_library()
