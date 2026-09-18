import pytest

from newtvshowsng2.config import Config


def test_username_required_and_trimmed(monkeypatch):
    monkeypatch.setenv("JELLYFIN_URL", "http://jellyfin.test")
    monkeypatch.setenv("JELLYFIN_API_KEY", "test-secret")
    monkeypatch.setenv("RSS_URLS", "https://feed.test/rss")
    monkeypatch.delenv("JELLYFIN_USERNAME", raising=False)
    with pytest.raises(ValueError, match="JELLYFIN_USERNAME"):
        Config.from_env()
    monkeypatch.setenv("JELLYFIN_USERNAME", "   ")
    with pytest.raises(ValueError, match="JELLYFIN_USERNAME"):
        Config.from_env()
    monkeypatch.setenv("JELLYFIN_USERNAME", " Hans ")
    assert Config.from_env().jellyfin_username == "Hans"
