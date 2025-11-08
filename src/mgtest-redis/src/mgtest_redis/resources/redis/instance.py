import logging
import socket
import subprocess

from mgtest.api import ResourceInstance, retry

logger = logging.getLogger(__name__)


class RedisInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._container_id = None

    def setup(self):
        logger.debug("Starting Redis container")
        command = ["docker", "run", "--detach", *self.definition.docker_args]
        command.extend(("--publish", f"{self.definition.port or 0}:6379", self.definition.image))
        if self.definition.password:
            command.extend(("redis-server", "--requirepass", self.definition.password))
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        self._container_id = result.stdout.strip()
        port = self._published_port()
        self.outputs.host = self.definition.host
        self.outputs.port = port
        self.outputs.database = self.definition.database
        self.outputs.url = f"redis://{self.definition.host}:{port}/{self.definition.database}"
        self.outputs.container_id = self._container_id
        logger.debug("Waiting for Redis to accept connections")
        retry(self._connect, timeout=self.definition.timeout, interval=self.definition.interval)

    def teardown(self):
        if self._container_id and self.definition.delete_on_teardown:
            logger.debug("Removing Redis container")
            subprocess.run(
                ["docker", "rm", "--force", self._container_id],
                check=False,
                text=True,
                capture_output=True,
            )

    def _published_port(self) -> int:
        result = subprocess.run(
            ["docker", "port", self._container_id, "6379/tcp"],
            check=True,
            text=True,
            capture_output=True,
        )
        return int(result.stdout.strip().rsplit(":", 1)[1])

    def _connect(self):
        address = self.outputs.host, self.outputs.port
        with socket.create_connection(address, timeout=self.definition.interval):
            pass
