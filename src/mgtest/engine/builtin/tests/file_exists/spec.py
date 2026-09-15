from typing import Literal

from mgtest.engine.api.test.spec import TestSpec
from mgtest.engine.builtin.tests.file_exists.instance import FileExistsInstance


class FileExistsSpec(TestSpec):
    TYPE = "FileExists"

    type: Literal["FileExists"]
    path: str

    class Inputs(TestSpec.Inputs):
        path: str

    class Outputs(TestSpec.Outputs):
        exists: bool = False

    def create_instance(self) -> "FileExistsInstance":
        return FileExistsInstance(self)
