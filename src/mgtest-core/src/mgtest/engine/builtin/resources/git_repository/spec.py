from pathlib import Path

from pydantic import BaseModel

from mgtest.api.resource import ResourceSpec
from mgtest.engine.builtin.resources.git_repository.instance import GitRepositoryInstance


class GitRepository(ResourceSpec):
    """Clone a Git repository at a selected revision into a local directory."""

    url: str
    path: Path
    ref: str | None = None
    depth: int | None = None
    submodules: bool = False
    clean: bool = False

    class Output(BaseModel):
        path: Path | None = None
        revision: str = ""

    def create_instance(self) -> GitRepositoryInstance:
        return GitRepositoryInstance(self)
