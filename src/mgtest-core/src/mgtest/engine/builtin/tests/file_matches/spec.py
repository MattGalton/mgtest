from pathlib import Path

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.file_matches.instance import FileMatchesInstance


class FileMatches(TestSpec):
    """Read a file and assert its content equals, contains, or matches text."""

    path: str | Path = Field(description="File whose text content is checked.")
    contains: str | None = Field(default=None, description="Text that must occur in the file.")
    equals: str | None = Field(default=None, description="Exact text required for the whole file.")
    matches: str | None = Field(default=None, description="Regular expression that must match the file content.")
    timeout: float | None = Field(default=None, gt=0, description="Maximum seconds to wait; omit to check once.")
    interval: float = Field(default=0.1, gt=0, description="Seconds between file reads while waiting.")

    class Output(BaseModel):
        content: str = Field(default="", description="File content read by the successful check.")

    def create_instance(self) -> FileMatchesInstance:
        return FileMatchesInstance(self)
