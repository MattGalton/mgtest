"""Runtime implementation for semantic JSON baseline comparisons."""

import json
import logging
from pathlib import Path

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.tests.baseline import baseline_path

logger = logging.getLogger(__name__)


class JsonBaselineInstance(TestInstance):
    """Compare parsed JSON values with their checked-in baseline."""

    def run(self, resources) -> None:
        """Load the generated and baseline documents and compare their values."""
        logger.debug(
            "Comparing JSON %s with baseline %s", self.definition.path, self.definition.baseline
        )
        document = self._compare()
        self.outputs.document = document

    def _compare(self):
        actual = json.loads(Path(self.definition.path).read_text())
        baseline = baseline_path(self.definition.baseline, self.definition.source_path)
        expected = json.loads(baseline.read_text())
        assert actual == expected, f"JSON differs from baseline: {baseline}"
        return actual
