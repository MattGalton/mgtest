import logging
import os
from pathlib import Path

from mgtest.env import MGT_LOG_LEVEL

LOG_FORMAT = "[%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_LEVEL = logging.INFO
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def configured_level() -> int | None:
    """Return the level selected through ``MGT_LOG_LEVEL``, when set."""
    value = os.environ.get(MGT_LOG_LEVEL)
    if value is None:
        return None
    level = logging.getLevelNamesMapping().get(value.upper())
    if not isinstance(level, int):
        raise ValueError(f"{MGT_LOG_LEVEL} must be a standard logging level, got {value!r}")
    return level


def setup_logging(level: int | None = None, log_file: Path | None = None) -> None:
    """Configure the ``mgtest`` logger for command-line use.

    Library code only obtains named loggers.  This function is deliberately
    called by the CLI entry point, leaving pytest and embedding applications in
    control of their own logging handlers and capture settings.
    """
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handlers.append(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(file_handler)

    resolved_level = configured_level() if level is None else level
    logger = logging.getLogger("mgtest")
    logger.setLevel(DEFAULT_LEVEL if resolved_level is None else resolved_level)
    logger.handlers.clear()
    logger.propagate = False
    for handler in handlers:
        logger.addHandler(handler)
