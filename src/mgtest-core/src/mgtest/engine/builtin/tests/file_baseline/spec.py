"""Definition for exact file baseline comparisons."""

from pathlib import Path

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.file_baseline.instance import FileBaselineInstance


class FileBaseline(TestSpec):
    """Compare a generated file byte-for-byte with a checked-in baseline file."""

    path: str | Path = Field(description="Generated file to compare.")
    baseline: Path = Field(description="Checked-in file used as the expected baseline.")

    class Output(BaseModel):
        """Details of the compared files."""

        path: Path = Field(default=Path(), description="Generated file that was compared.")
        baseline: Path = Field(default=Path(), description="Baseline file used for comparison.")
        bytes: int = Field(default=0, description="Number of bytes compared.")

    def create_instance(self) -> FileBaselineInstance:
        """Create the exact-file comparator."""
        return FileBaselineInstance(self)
