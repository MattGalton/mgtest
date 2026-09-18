from typing import Any

from pydantic import BaseModel, Field

from mgtest.api.resource import ResourceSpec
from mgtest.engine.builtin.resources.executable.instance import ExecutableInstance


class Executable(ResourceSpec):
    """Start and supervise a local executable for checks that use its output."""

    path: str = Field(..., description="Path to the executable")
    args: list[str] = Field(default_factory=list, description="Arguments for the executable")
    max_output_bytes: int = Field(default=1024 * 1024, ge=4096)

    class Output(BaseModel):
        exe: Any | None = Field(default=None, description="The executable instance")

    def create_instance(self) -> ExecutableInstance:
        return ExecutableInstance(self)
