"""Runtime implementation for recursive directory baseline comparisons."""

import logging
from pathlib import Path

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.tests.baseline import baseline_path

logger = logging.getLogger(__name__)


class DirectoryBaselineInstance(TestInstance):
    """Compare directory structure, file contents, and symlink targets."""

    def run(self, resources) -> None:
        """Compare the generated directory tree with its baseline."""
        logger.debug(
            "Comparing directory %s with baseline %s",
            self.definition.path,
            self.definition.baseline,
        )
        entries = self._compare()
        self.outputs.entries = entries

    def _compare(self) -> list[str]:
        actual = _tree(Path(self.definition.path))
        baseline = baseline_path(self.definition.baseline, self.definition.source_path)
        expected = _tree(baseline)
        assert actual == expected, (
            f"Directory differs from baseline: {baseline}"
        )
        return sorted(actual)


def _tree(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
    """Return a portable representation of all entries below *root*."""
    assert root.is_dir(), f"Directory does not exist: {root}"
    entries = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[relative] = ("symlink", path.readlink().as_posix())
        elif path.is_dir():
            entries[relative] = ("directory", None)
        elif path.is_file():
            entries[relative] = ("file", path.read_bytes())
        else:
            raise AssertionError(f"Unsupported directory entry: {path}")
    return entries
