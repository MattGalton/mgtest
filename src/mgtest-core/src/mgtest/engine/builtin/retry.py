from __future__ import annotations

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def retry[T](action: Callable[[], T], *, timeout: float, interval: float) -> T:
    """Run an assertion-like action until it succeeds or its deadline expires."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return action()
        except (AssertionError, OSError) as error:
            if time.monotonic() >= deadline:
                logger.debug("Retry deadline reached after %.1fs: %s", timeout, error)
                raise error
            logger.debug("Retrying after transient failure: %s", error)
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
