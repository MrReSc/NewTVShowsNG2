import ctypes
import errno
import os
import struct
from dataclasses import replace
from pathlib import Path

import pytest

from newtvshowsng2 import filesystem, import_preflight
from newtvshowsng2.config import Config


def test_preflight_reports_common_mount_without_writing(tmp_path):
    income, shows = tmp_path / "income", tmp_path / "shows"
    income.mkdir()
    shows.mkdir()
    before = filesystem.snapshot(tmp_path)
    result = filesystem.preflight(income, shows)
    assert result["income"] == result["shows"]
    assert filesystem.snapshot(tmp_path) == before


@pytest.mark.parametrize("field,value", [("mount", -1), ("device", -1), ("subvolume", 123)])
def test_distinct_filesystems_are_blocked(tmp_path, monkeypatch, field, value):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    original = filesystem.identity

    def changed(descriptor, mounts=None):
        current = original(descriptor, mounts)
        if os.fstat(descriptor).st_ino == target.stat().st_ino:
            return replace(current, **{field: value})
        return current

    monkeypatch.setattr(filesystem, "identity", changed)
    with pytest.raises(filesystem.FilesystemBlocked) as raised:
        filesystem.check_pair(source, target)
    assert raised.value.details["source"] != raised.value.details["target"]


@pytest.mark.parametrize("field", ["mount", "subvolume"])
def test_nested_mount_or_subvolume_is_rejected(tmp_path, monkeypatch, field):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "video.mkv").write_bytes(b"video")
    original = filesystem.identity

    def changed(descriptor, mounts=None):
        current = original(descriptor, mounts)
        if os.fstat(descriptor).st_ino == nested.stat().st_ino:
            return replace(current, **{field: -1})
        return current

    monkeypatch.setattr(filesystem, "identity", changed)
    with pytest.raises(filesystem.FilesystemBlocked):
        filesystem.snapshot(tmp_path)


def test_btrfs_lookup_uses_unprivileged_root_id_case(monkeypatch):
    def ioctl(descriptor, request, arguments, mutate):
        assert descriptor == 123
        assert request == 0xD0009412
        assert len(arguments) == 4096
        assert struct.unpack_from("=QQ", arguments) == (0, 256)
        struct.pack_into("=Q", arguments, 0, 987)

    monkeypatch.setattr(filesystem.fcntl, "ioctl", ioctl)
    assert filesystem._subvolume(123) == 987


def test_rename_never_overwrites_existing_target(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"source")
    target.write_bytes(b"target")
    with filesystem.open_path(tmp_path) as descriptor:
        with pytest.raises(filesystem.FilesystemBlocked, match="existiert bereits"):
            filesystem.rename_noreplace(descriptor, source.name, descriptor, target.name)
    assert source.read_bytes() == b"source"
    assert target.read_bytes() == b"target"


@pytest.mark.parametrize("error", [errno.EXDEV, errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP, errno.EACCES, errno.EPERM])
def test_native_rename_failure_is_blocked_without_fallback(tmp_path, monkeypatch, error):
    source = tmp_path / "source"
    source.write_bytes(b"source")

    def failed(*args):
        ctypes.set_errno(error)
        return -1

    monkeypatch.setattr(filesystem, "_rename_function", lambda: failed)
    with filesystem.open_path(tmp_path) as descriptor:
        with pytest.raises(filesystem.FilesystemBlocked):
            filesystem.rename_noreplace(descriptor, "source", descriptor, "target")
    assert source.read_bytes() == b"source"
    assert not (tmp_path / "target").exists()


def test_missing_libc_function_is_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(ctypes, "CDLL", lambda *a, **k: object())
    with pytest.raises(filesystem.FilesystemBlocked, match="nicht unterstützt"):
        filesystem.check_pair(tmp_path, tmp_path)


def test_symlinked_ancestor_and_payload_are_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "nested").mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        with filesystem.open_path(link / "nested"):
            pass
    (real / "video.mkv").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(OSError):
        filesystem.snapshot(real)


@pytest.mark.parametrize("valid", [False, True])
def test_diagnostic_runs_read_only_with_configured_identity(tmp_path, monkeypatch, capsys, valid):
    income, shows = tmp_path / "income", tmp_path / "shows"
    income.mkdir()
    shows.mkdir()
    config = Config("http://unused", "secret", ("http://unused",), "unused", income_dir=income, shows_dir=shows)
    monkeypatch.setenv("PUID", "1234")
    monkeypatch.setenv("PGID", "5678")
    monkeypatch.setattr(import_preflight.Config, "from_env", lambda: config)
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    calls = []
    monkeypatch.setattr(os, "setgroups", lambda groups: calls.append(("groups", groups)))
    monkeypatch.setattr(os, "setgid", lambda gid: calls.append(("gid", gid)))
    monkeypatch.setattr(os, "setuid", lambda uid: calls.append(("uid", uid)))
    if not valid:
        shows.rmdir()
    before = filesystem.snapshot(tmp_path)
    assert import_preflight.main() == (0 if valid else 1)
    assert calls == [("groups", []), ("gid", 5678), ("uid", 1234)]
    assert filesystem.snapshot(tmp_path) == before
    output = capsys.readouterr()
    assert "secret" not in output.out + output.err
    if valid:
        assert '"mount"' in output.out


def test_diagnostic_does_not_claim_success_for_wrong_uid(monkeypatch, capsys):
    monkeypatch.setenv("PUID", "999")
    monkeypatch.setenv("PGID", "999")
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    monkeypatch.setattr(os, "getegid", lambda: 1000)
    assert import_preflight.main() == 1
    assert "PUID" in capsys.readouterr().err
