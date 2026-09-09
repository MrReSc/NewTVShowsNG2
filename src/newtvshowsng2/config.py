from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True, slots=True)
class Config:
    jellyfin_url: str
    jellyfin_api_key: str
    rss_urls: tuple[str, ...]
    check_interval_hours: float = 1.0
    max_history: int = 300
    timezone: str = "Europe/Zurich"
    port: int = 8080
    log_level: str = "INFO"
    data_dir: Path = Path("/data")
    output_dir: Path = Path("/out")
    request_timeout: float = 20.0

    @property
    def database_path(self) -> Path:
        return self.data_dir / "newtvshowsng2.sqlite3"

    @property
    def output_path(self) -> Path:
        return self.output_dir / "index.html"

    @property
    def interval_seconds(self) -> float:
        return self.check_interval_hours * 3600

    @classmethod
    def from_env(cls) -> Config:
        jellyfin_url = _required("JELLYFIN_URL").rstrip("/")
        jellyfin_api_key = _required("JELLYFIN_API_KEY")
        rss_urls = tuple(
            value.strip()
            for value in _required("RSS_URLS").replace("\n", ",").split(",")
            if value.strip()
        )
        if not rss_urls:
            raise ValueError("RSS_URLS muss mindestens eine URL enthalten")

        interval = _positive_float("CHECK_INTERVAL_HOURS", 1.0)
        max_history = _positive_int("MAX_HISTORY", 300)
        port = _positive_int("PORT", 8080)
        if port > 65535:
            raise ValueError("PORT muss zwischen 1 und 65535 liegen")

        timezone = os.getenv("TZ", "Europe/Zurich")
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unbekannte Zeitzone in TZ: {timezone}") from exc

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in logging.getLevelNamesMapping():
            raise ValueError(f"Ungültiges LOG_LEVEL: {log_level}")

        return cls(
            jellyfin_url=jellyfin_url,
            jellyfin_api_key=jellyfin_api_key,
            rss_urls=rss_urls,
            check_interval_hours=interval,
            max_history=max_history,
            timezone=timezone,
            port=port,
            log_level=log_level,
            data_dir=Path(os.getenv("DATA_DIR", "/data")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "/out")),
            request_timeout=_positive_float("REQUEST_TIMEOUT_SECONDS", 20.0),
        )


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Erforderliche Umgebungsvariable fehlt: {name}")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} muss eine ganze Zahl sein") from exc
    if value <= 0:
        raise ValueError(f"{name} muss größer als 0 sein")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} muss eine Zahl sein") from exc
    if value <= 0:
        raise ValueError(f"{name} muss größer als 0 sein")
    return value
