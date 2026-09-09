from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    uid = _numeric_id("PUID", 10001)
    gid = _numeric_id("PGID", 10001)
    paths = (
        Path(os.getenv("DATA_DIR", "/data")),
        Path(os.getenv("OUTPUT_DIR", "/out")),
    )

    for path in paths:
        _prepare_directory(path, uid, gid)

    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)

    os.execvp("newtvshowsng2", ["newtvshowsng2"])


def _numeric_id(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} muss eine numerische Benutzer-ID sein") from exc
    if value < 0:
        raise ValueError(f"{name} darf nicht negativ sein")
    return value


def _prepare_directory(path: Path, uid: int, gid: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.geteuid() != 0:
        if not os.access(path, os.W_OK | os.X_OK):
            raise PermissionError(f"Kein Schreibzugriff auf {path}")
        return

    for root, directories, files in os.walk(path, followlinks=False):
        os.chown(root, uid, gid, follow_symlinks=False)
        for name in (*directories, *files):
            child = Path(root, name)
            try:
                os.chown(child, uid, gid, follow_symlinks=False)
            except FileNotFoundError:
                continue


if __name__ == "__main__":
    main()
