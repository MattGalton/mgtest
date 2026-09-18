from __future__ import annotations

import logging
import subprocess

from mgtest.api import ResourceInstance

logger = logging.getLogger(__name__)


class DockerContainerInstance(ResourceInstance):
    def setup(self):
        logger.debug("Starting Docker image %s", self.definition.image)
        command = ["docker", "run", "--detach", *self.definition.docker_args]
        for name, value in self.definition.environment.items():
            command.extend(("--env", f"{name}={value}"))
        for container_port, host_port in self.definition.ports.items():
            command.extend(("--publish", f"{host_port or 0}:{container_port}"))
        command.extend((self.definition.image, *self.definition.command))
        completed = subprocess.run(command, check=True, text=True, capture_output=True)
        self._container_id = completed.stdout.strip()
        self.outputs.container_id = self._container_id
        self.outputs.ports = self._published_ports()

    def teardown(self):
        if hasattr(self, "_container_id"):
            logger.debug("Removing Docker container")
            subprocess.run(
                ["docker", "rm", "--force", self._container_id],
                check=False,
                text=True,
                capture_output=True,
            )

    def logs(self) -> str:
        completed = subprocess.run(
            ["docker", "logs", self._container_id], check=True, text=True, capture_output=True
        )
        return completed.stdout + completed.stderr

    def _published_ports(self) -> dict[int, int]:
        completed = subprocess.run(
            ["docker", "port", self._container_id], check=True, text=True, capture_output=True
        )
        result = {}
        for line in completed.stdout.splitlines():
            container, _, host = line.partition(" -> ")
            if not host:
                continue
            result[int(container.split("/", 1)[0])] = int(host.rsplit(":", 1)[1])
        return result
