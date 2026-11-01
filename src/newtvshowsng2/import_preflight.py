from __future__ import annotations

import json
import os
import sys

from .config import Config
from .entrypoint import _numeric_id
from .filesystem import FilesystemBlocked, preflight


def main() -> int:
    try:
        uid = _numeric_id("PUID", 10001)
        gid = _numeric_id("PGID", 10001)
        if os.geteuid() == 0:
            identity_changed = os.geteuid() != uid or os.getegid() != gid
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
            if identity_changed:
                # A credential change restricts proc ownership on older kernels.
                # Re-exec matches the service entrypoint without widening rights.
                os.execv(
                    sys.executable,
                    [sys.executable, "-m", "newtvshowsng2.import_preflight"],
                )
        elif os.geteuid() != uid or os.getegid() != gid:
            raise FilesystemBlocked("Diagnose muss unter den konfigurierten PUID und PGID laufen")
        config = Config.from_env()
        result = preflight(config.income_dir, config.shows_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("Vorprüfung erfolgreich. Der Import prüft die konkrete Verschiebung zusätzlich.")
        return 0
    except (FilesystemBlocked, OSError, ValueError, KeyError) as exc:
        if isinstance(exc, FilesystemBlocked) and exc.details is not None:
            print(json.dumps(exc.details, ensure_ascii=False, indent=2))
        print(f"Vorprüfung fehlgeschlagen: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
