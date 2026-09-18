"""Runtime implementation for exact file baseline comparisons."""

import logging
from pathlib import Path

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.tests.baseline import baseline_path

logger = logging.getLogger(__name__)


class FileBaselineInstance(TestInstance):
    """Compare a generated file to its checked-in baseline."""

    def run(self, resources) -> None:
        """Read both files and fail unless their bytes are identical."""
        logger.debug(
            "Comparing file %s with baseline %s", self.definition.path, self.definition.baseline
        )
        size = self._compare()
        self.outputs.path = Path(self.definition.path)
        self.outputs.baseline = baseline_path(
            self.definition.baseline, self.definition.source_path
        )
        self.outputs.bytes = size

    def _compare(self) -> int:
        actual = Path(self.definition.path).read_bytes()
        baseline = baseline_path(self.definition.baseline, self.definition.source_path)
        expected = baseline.read_bytes()
        assert actual == expected, f"File differs from baseline: {baseline}"
        return len(actual)
