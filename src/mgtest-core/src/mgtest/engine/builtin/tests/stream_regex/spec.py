import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.stream_regex.instance import StreamRegexTestInstance


class StreamRegex(TestSpec):
    """Wait for a byte regular expression in an Executable output stream."""


    class Output(BaseModel):
        found: bool = Field(default=False, description="Whether the pattern was found.")

    resource: str = Field(description="Visible Executable resource whose output is monitored.")
    pattern: str = Field(description="Byte regular expression required in the selected stream.")
    stream: Literal["stdout", "stderr"] = Field(default="stdout", description="Executable output stream to monitor.")
    timeout: float = Field(default=10.0, gt=0, allow_inf_nan=False, description="Maximum seconds to wait for the pattern.")

    @field_validator("pattern")
    @classmethod
    def valid_pattern(cls, value: str) -> str:
        try:
            re.compile(value.encode())
        except re.error as error:
            raise ValueError(f"Invalid byte regex: {error}") from error
        return value

    def validate_resources(self, resources):
        if self.resource not in resources:
            raise ValueError(f"Test '{self.name}' references unknown resource '{self.resource}'")

    def create_instance(self) -> StreamRegexTestInstance:
        return StreamRegexTestInstance(self)
