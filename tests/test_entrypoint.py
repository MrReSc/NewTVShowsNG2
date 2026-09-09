from __future__ import annotations

import os

import pytest

from newtvshowsng2.entrypoint import _numeric_id, _prepare_directory


def test_numeric_id_uses_default_and_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PUID", raising=False)
    assert _numeric_id("PUID", 10001) == 10001

    monkeypatch.setenv("PUID", "1234")
    assert _numeric_id("PUID", 10001) == 1234


@pytest.mark.parametrize("value", ["abc", "-1"])
def test_numeric_id_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("PUID", value)
    with pytest.raises(ValueError):
        _numeric_id("PUID", 10001)


def test_prepare_directory_is_writable(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "data"
    monkeypatch.setattr(os, "geteuid", lambda: 1000)

    _prepare_directory(target, 1000, 1000)

    assert target.is_dir()
    assert os.access(target, os.W_OK | os.X_OK)
