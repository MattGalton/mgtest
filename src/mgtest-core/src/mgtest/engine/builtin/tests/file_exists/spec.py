from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.file_exists.instance import FileExistsInstance


class FileExists(TestSpec):
    """Assert that a file or directory exists at the configured path."""

    path: str = Field(description="File system path that must exist.")
    timeout: float | None = Field(default=None, gt=0, description="Maximum seconds to wait; omit to check once.")
    interval: float = Field(default=0.1, gt=0, description="Seconds between existence checks while waiting.")

    class Output(BaseModel):
        exists: bool = Field(default=False, description="Whether the path existed when the check completed.")

    def create_instance(self) -> "FileExistsInstance":
        return FileExistsInstance(self)
