from typing import Any, Literal

from pydantic import BaseModel, Field

from mgtest.engine.api.resource.spec import ResourceSpec
from mgtest.engine.builtin.resources.executable.instance import ExecutableInstance


class ExecutableDefinition(ResourceSpec):
    TYPE = "Executable"

    type: Literal["Executable"]
    path: str = Field(..., description="Path to the executable")
    args: list[str] = Field(default_factory=list, description="Arguments for the executable")

    class Inputs(BaseModel):
        path: str = Field(..., description="Path to the executable")
        args: list[str] = Field(default_factory=list, description="Arguments for the executable")

    class Outputs(BaseModel):
        exe: Any | None = Field(default=None, description="The executable instance")

    def create_instance(self) -> "ResourceInstance":
        return ExecutableInstance(self)
