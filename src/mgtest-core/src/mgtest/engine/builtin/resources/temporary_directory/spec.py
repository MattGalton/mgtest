from pydantic import BaseModel

from mgtest.api.resource import ResourceSpec
from mgtest.engine.builtin.resources.temporary_directory.instance import TemporaryDirectoryInstance


class TemporaryDirectory(ResourceSpec):
    """Create a temporary directory and optionally remove it during teardown."""

    prefix: str = "mgtest-"
    parent: str | None = None
    delete_on_teardown: bool = True

    class Output(BaseModel):
        path: str = ""

    def create_instance(self) -> TemporaryDirectoryInstance:
        return TemporaryDirectoryInstance(self)
