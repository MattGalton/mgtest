from __future__ import annotations

import logging
import re
from pathlib import Path

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.retry import retry

logger = logging.getLogger(__name__)


class FileMatchesInstance(TestInstance):
    def run(self, resources):
        logger.debug("Reading file %s for content assertions", self.definition.path)
        check = self._read_and_assert
        content = (
            retry(check, timeout=self.definition.timeout, interval=self.definition.interval)
            if self.definition.timeout is not None
            else check()
        )
        self.outputs.content = content

    def _read_and_assert(self):
        content = Path(self.definition.path).read_text()
        if self.definition.contains is not None:
            assert self.definition.contains in content, content
        if self.definition.equals is not None:
            assert content == self.definition.equals, content
        if self.definition.matches is not None:
            assert re.search(self.definition.matches, content), content
        return content
