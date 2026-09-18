"""Definition for recursive directory baseline comparisons."""

from pathlib import Path

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.directory_baseline.instance import DirectoryBaselineInstance


class DirectoryBaseline(TestSpec):
    """Compare a generated directory tree with checked-in files and directories."""

    path: str | Path = Field(description="Generated directory tree to compare.")
    baseline: Path = Field(description="Checked-in directory tree used as the expected baseline.")

    class Output(BaseModel):
        """The relative entries found in the generated tree."""

        entries: list[str] = Field(
            default_factory=list, description="Relative paths found in the generated tree."
        )

    def create_instance(self) -> DirectoryBaselineInstance:
        """Create the recursive directory comparator."""
        return DirectoryBaselineInstance(self)
