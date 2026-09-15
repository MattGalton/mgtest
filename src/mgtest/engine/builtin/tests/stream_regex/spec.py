from typing import Literal

from mgtest.engine.api.test.spec import TestSpec
from mgtest.engine.builtin.tests.stream_regex.instance import StreamRegexTestInstance


class StreamRegexTestDefinition(TestSpec):
    TYPE = "StreamRegex"
    type: Literal["StreamRegex"]

    class Outputs(TestSpec.Outputs):
        found: bool = False

    resource: str
    pattern: str

    def create_instance(self) -> "StreamRegexTestInstance":
        return StreamRegexTestInstance(self)
