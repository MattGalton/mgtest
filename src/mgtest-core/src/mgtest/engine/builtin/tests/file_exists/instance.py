import logging

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.retry import retry

logger = logging.getLogger(__name__)


class FileExistsInstance(TestInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._path = definition.path
        self.exists = False

    def run(self, resources):
        import os

        logger.debug("Checking whether %s exists", self._path)
        self.exists = (
            retry(
                lambda: self._check_exists(os),
                timeout=self.definition.timeout,
                interval=self.definition.interval,
            )
            if self.definition.timeout is not None
            else self._check_exists(os)
        )
        # Perhaps set outputs
        self.outputs.exists = self.exists
        if not self.exists:
            raise AssertionError(f"Path does not exist: {self._path}")

    def _check_exists(self, os):
        exists = os.path.exists(self._path)
        if not exists:
            raise AssertionError(f"Path does not exist: {self._path}")
        return exists

    def setup(self):
        pass

    def teardown(self):
        pass

    def value(self):
        return self.exists
