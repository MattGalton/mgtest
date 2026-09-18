from pathlib import Path

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.archive_contains.instance import ArchiveContainsInstance


class ArchiveContains(TestSpec):
    """Assert that a ZIP or tar archive contains each required entry."""

    path: Path = Field(description="Path to the ZIP or tar archive to inspect.")
    contains: list[str] = Field(min_length=1, description="Archive entry names that must be present.")
    timeout: float | None = Field(default=None, gt=0, description="Maximum seconds to wait; omit to check once.")
    interval: float = Field(default=0.1, gt=0, description="Seconds between checks while waiting.")

    class Output(BaseModel):
        entries: list[str] = Field(default_factory=list, description="Entry names found in the archive.")

    def create_instance(self) -> ArchiveContainsInstance:
        return ArchiveContainsInstance(self)
