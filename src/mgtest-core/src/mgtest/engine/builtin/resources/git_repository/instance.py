from __future__ import annotations

import logging
import subprocess

from mgtest.api.resource import ResourceInstance
from mgtest.runtime.context import current_workspace

logger = logging.getLogger(__name__)


class GitRepositoryInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._prepared = False

    def prepare(self):
        if self._prepared:
            return
        path = self.definition.path
        if (path / ".git").is_dir():
            logger.debug("Fetching Git repository at %s", path)
            self._git("fetch", "--tags", "--force", cwd=path)
        elif path.exists():
            raise ValueError(f"GitRepository path exists but is not a repository: {path}")
        else:
            logger.debug("Cloning Git repository into %s", path)
            command = ["clone"]
            if self.definition.depth:
                command.extend(("--depth", str(self.definition.depth)))
            workspace = current_workspace()
            if workspace:
                mirror = workspace.cache.directory("git", self.definition.url)
                cache_hit = (mirror / "HEAD").exists()
                workspace.cache.record_result(mirror, hit=cache_hit)
                if cache_hit:
                    self._git("--git-dir", str(mirror), "fetch", "--prune", "--tags")
                else:
                    self._git("clone", "--mirror", self.definition.url, str(mirror))
                command.extend(("--reference-if-able", str(mirror)))
            command.extend((self.definition.url, str(path)))
            self._git(*command)
        if self.definition.ref:
            logger.debug("Checking out Git ref %s", self.definition.ref)
            self._git("checkout", "--force", self.definition.ref, cwd=path)
        if self.definition.clean:
            self._git("clean", "--force", "--directories", cwd=path)
        if self.definition.submodules:
            self._git("submodule", "update", "--init", "--recursive", cwd=path)
        self.outputs.path = path
        self.outputs.revision = self._git("rev-parse", "HEAD", cwd=path).stdout.strip()
        self._prepared = True

    def setup(self):
        self.prepare()

    def teardown(self):
        pass

    @staticmethod
    def _git(*arguments: str, cwd=None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments], check=True, text=True, capture_output=True, cwd=cwd
        )
