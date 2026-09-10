from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUP_COUNT = 1
LOG_PAGE_LINES = 500


def configure_logging(log_path: Path, level: str) -> None:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level))
    root.handlers.clear()
    root.addHandler(stream_handler)
    root.addHandler(file_handler)


def read_recent_log_lines(log_path: Path, limit: int = LOG_PAGE_LINES) -> list[str]:
    lines: list[str] = []
    for path in (log_path.with_name(f"{log_path.name}.1"), log_path):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            lines.extend(content.splitlines())
        except FileNotFoundError:
            continue
        except OSError as exc:
            lines.append(f"Logdatei konnte nicht gelesen werden: {exc}")
    return lines[-limit:]
