import logging
from pathlib import Path

LOG_FORMAT = "[%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_LEVEL = logging.INFO


def setup_logging(level: int = DEFAULT_LEVEL, log_file: Path | None = None) -> None:
    """
    Configure default logging for mgtest.

    - level: default logging level
    - log_file: optional file to log to (if None, logs go to stdout)
    """
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handlers.append(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)
