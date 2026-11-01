from __future__ import annotations

import ctypes
import errno
import fcntl
import os
import stat
import struct
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path


class FilesystemBlocked(RuntimeError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details


@dataclass(frozen=True)
class FilesystemIdentity:
    device: int
    mount: int
    filesystem: str
    subvolume: int | None


@contextmanager
def open_path(path: Path) -> Iterator[int]:
    """Anchor every component so a symlink cannot redirect a later operation."""
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        parts = path.absolute().parts[1:]
        for index, part in enumerate(parts):
            if part in (".", ".."):
                raise FilesystemBlocked("Unsicherer Pfadbestandteil")
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _mount_types() -> dict[int, str]:
    result = {}
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = line.split()
        result[int(fields[0])] = fields[fields.index("-") + 1]
    return result


def _subvolume(descriptor: int) -> int:
    # The root-id lookup is the unprivileged special case, not a path lookup.
    arguments = bytearray(4096)
    struct.pack_into("=QQ", arguments, 0, 0, 256)
    fcntl.ioctl(descriptor, 0xD0009412, arguments, True)
    return struct.unpack_from("=Q", arguments)[0]


def identity(descriptor: int, mounts: dict[int, str] | None = None) -> FilesystemIdentity:
    mounts = _mount_types() if mounts is None else mounts
    fields = dict(
        line.split(":", 1)
        for line in Path(f"/proc/self/fdinfo/{descriptor}").read_text().splitlines()
        if ":" in line
    )
    mount = int(fields["mnt_id"].strip())
    filesystem = mounts[mount]
    return FilesystemIdentity(
        os.fstat(descriptor).st_dev, mount, filesystem,
        _subvolume(descriptor) if filesystem == "btrfs" else None,
    )


def _compatible(source: FilesystemIdentity, target: FilesystemIdentity) -> None:
    if source.mount != target.mount:
        raise FilesystemBlocked("Quelle und Ziel liegen auf unterschiedlichen Mounts")
    if source.subvolume != target.subvolume:
        raise FilesystemBlocked("Quelle und Ziel liegen in unterschiedlichen Btrfs-Untervolumes")
    if source.device != target.device:
        raise FilesystemBlocked("Quelle und Ziel liegen auf unterschiedlichen Dateisystemen")


def _rename_function():
    function = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if function is None:
        raise FilesystemBlocked("Sicheres Verschieben mit renameat2 wird nicht unterstützt")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    return function


def check_pair(source: Path, target_directory: Path) -> tuple[FilesystemIdentity, FilesystemIdentity]:
    _rename_function()
    with open_path(source) as source_fd, open_path(target_directory) as target_fd:
        first, second = identity(source_fd), identity(target_fd)
        try:
            _compatible(first, second)
        except FilesystemBlocked as exc:
            exc.details = {"source": asdict(first), "target": asdict(second)}
            raise
        return first, second


def preflight(income: Path, shows: Path) -> dict[str, dict]:
    if not income.is_absolute() or not shows.is_absolute():
        raise FilesystemBlocked("Income und Shows benötigen absolute Pfade")
    if income == shows or income in shows.parents or shows in income.parents:
        raise FilesystemBlocked("Income und Shows dürfen sich nicht überlappen")
    for path in (income, shows):
        with open_path(path) as descriptor:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise FilesystemBlocked(f"Kein Verzeichnis: {path}")
        if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
            raise FilesystemBlocked(f"Verzeichnis ist nicht les- und schreibbar: {path}")
    first, second = check_pair(income, shows)
    return {"income": asdict(first), "shows": asdict(second)}


def snapshot_fd(descriptor: int, *, sync: bool = False) -> dict[str, list[int | None]]:
    mounts = _mount_types()
    boundary = identity(descriptor, mounts)
    result = {}

    def visit(current: int, relative: str) -> None:
        location = identity(current, mounts)
        _compatible(boundary, location)
        details = os.fstat(current)
        if not (stat.S_ISDIR(details.st_mode) or stat.S_ISREG(details.st_mode)):
            raise FilesystemBlocked("Quelle enthält einen nicht unterstützten Dateityp")
        # ctime changes on rename. Inode, mode, size and mtime must survive it.
        result[relative] = [
            location.device, location.subvolume, details.st_ino,
            details.st_mode, details.st_size, details.st_mtime_ns,
        ]
        if stat.S_ISDIR(details.st_mode):
            for name in sorted(os.listdir(current)):
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
                try:
                    visit(child, name if relative == "." else f"{relative}/{name}")
                finally:
                    os.close(child)
        if sync:
            os.fsync(current)

    visit(descriptor, ".")
    return result


def snapshot(path: Path, *, sync: bool = False) -> dict[str, list[int | None]]:
    with open_path(path) as descriptor:
        return snapshot_fd(descriptor, sync=sync)


def rename_noreplace(source_fd: int, source: str, target_fd: int, target: str) -> None:
    _compatible(identity(source_fd), identity(target_fd))
    function = _rename_function()
    if function(source_fd, os.fsencode(source), target_fd, os.fsencode(target), 1) == 0:
        return
    error = ctypes.get_errno()
    descriptions = {
        errno.EEXIST: "Ein gleichnamiges Ziel existiert bereits",
        errno.EXDEV: "Dateisystemgrenze verhindert atomisches Verschieben",
        errno.ENOSYS: "Der Kernel unterstützt renameat2 nicht",
        errno.EINVAL: "Das Dateisystem unterstützt RENAME_NOREPLACE nicht",
        errno.EOPNOTSUPP: "Das Dateisystem unterstützt sicheres Verschieben nicht",
        errno.EACCES: "Fehlende Berechtigung zum Verschieben",
        errno.EPERM: "Verschieben wurde vom Dateisystem verweigert",
    }
    raise FilesystemBlocked(descriptions.get(error, f"Verschieben fehlgeschlagen: {os.strerror(error)}"))
