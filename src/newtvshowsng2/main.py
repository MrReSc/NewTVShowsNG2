from __future__ import annotations

import logging
import signal
import threading

from .config import Config
from .logging_utils import configure_logging
from .rendering import Renderer
from .scanner import Scanner
from .server import ApplicationServer
from .storage import Storage

LOGGER = logging.getLogger(__name__)


def main() -> None:
    try:
        config = Config.from_env()
    except ValueError as exc:
        raise SystemExit(f"Konfigurationsfehler: {exc}") from exc

    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(config.log_path, config.log_level)

    storage = Storage(config.database_path)
    storage.initialize()
    storage.recover_interrupted_manual_import()
    renderer = Renderer(
        storage, config.output_path, config.timezone, config.media_import_enabled
    )
    renderer.render()

    scanner = Scanner(config, storage, renderer)
    stop_event = threading.Event()

    def scheduler() -> None:
        while not stop_event.is_set():
            scanner.run()
            if stop_event.wait(config.interval_seconds):
                break

    scheduler_thread = threading.Thread(target=scheduler, name="scanner", daemon=True)
    scheduler_thread.start()

    server = ApplicationServer(
        ("0.0.0.0", config.port),
        config.output_path,
        storage,
        config.log_path,
        config.timezone,
        scanner,
    )

    def stop(_signum: int, _frame: object) -> None:
        LOGGER.info("Beende NewTVShowsNG2")
        stop_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    LOGGER.info("Website verfügbar auf Port %d", config.port)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        stop_event.set()
        server.server_close()
        scheduler_thread.join(timeout=10)


if __name__ == "__main__":
    main()
