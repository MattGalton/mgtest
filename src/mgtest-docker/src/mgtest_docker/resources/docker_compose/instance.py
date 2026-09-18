from __future__ import annotations

import logging
import os
import subprocess

from mgtest.api import ResourceInstance

logger = logging.getLogger(__name__)


class DockerComposeInstance(ResourceInstance):
    def setup(self):
        self._command = ["docker", "compose"]
        for path in self.definition.files:
            self._command.extend(("--file", str(path)))
        if self.definition.project_name:
            self._command.extend(("--project-name", self.definition.project_name))
        self._environment = os.environ | self.definition.environment
        self._run("up", "--detach", *self.definition.services)
        self.outputs.containers = self._run("ps", "--quiet").stdout.split()

    def teardown(self):
        if hasattr(self, "_command"):
            arguments = ["down"]
            if self.definition.remove_volumes:
                arguments.append("--volumes")
            self._run(*arguments, check=False)

    def logs(self, service: str | None = None) -> str:
        arguments = ["logs", "--no-color"]
        if service:
            arguments.append(service)
        result = self._run(*arguments)
        return result.stdout + result.stderr

    def _run(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        logger.debug("Running docker compose %s", " ".join(arguments))
        return subprocess.run(
            [*self._command, *arguments],
            check=check,
            text=True,
            capture_output=True,
            cwd=self.definition.working_directory,
            env=self._environment,
        )
