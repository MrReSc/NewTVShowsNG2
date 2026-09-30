from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 9
LOG_PAGE_ENTRIES = 100
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
LOG_HEADER = re.compile(
    r"^(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"
    r"(?:[,\.]\d+)?(?:Z|[+-]\d{2}:?\d{2})?) "
    r"(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL) "
    r"(?P<source>[^:]+): (?P<message>.*)$"
)


@dataclass(slots=True)
class LogEntry:
    timestamp: datetime | None
    level: str
    source: str
    message: str
    _detail_lines: list[str] = field(default_factory=list)

    @property
    def details(self) -> str:
        return "\n".join(self._detail_lines)


class UTCFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created, UTC).isoformat(timespec="seconds")


def configure_logging(log_path: Path, level: str) -> None:
    formatter = UTCFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
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


def _log_paths(log_path: Path) -> list[Path]:
    return [
        log_path.with_name(f"{log_path.name}.{index}")
        for index in range(LOG_BACKUP_COUNT, 0, -1)
    ] + [log_path]


def read_log_entries(log_path: Path, timezone: ZoneInfo) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for path in _log_paths(log_path):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        except OSError as exc:
            entries.append(LogEntry(None, "ERROR", "Log", f"{path.name} konnte nicht gelesen werden: {exc}"))
            continue
        for line in content.splitlines():
            match = LOG_HEADER.match(line)
            if match:
                try:
                    raw_time = match["time"].replace(",", ".").replace("Z", "+00:00")
                    timestamp = datetime.fromisoformat(raw_time)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone)
                    entries.append(LogEntry(timestamp, match["level"], match["source"], match["message"]))
                    continue
                except ValueError:
                    pass
            if entries:
                entries[-1]._detail_lines.append(line)
            elif line:
                entries.append(LogEntry(None, "INFO", "Log", line))
    return entries
