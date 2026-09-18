import logging
import subprocess

import psycopg
from mgtest.api import ResourceInstance, retry

logger = logging.getLogger(__name__)


class PostgresInstance(ResourceInstance):
    def __init__(self, definition):
        super().__init__(definition)
        self._container_id = None

    def setup(self):
        logger.debug("Starting Postgres container")
        command = ["docker", "run", "--detach", *self.definition.docker_args]
        command.extend(("--env", f"POSTGRES_DB={self.definition.database}"))
        command.extend(("--env", f"POSTGRES_USER={self.definition.user}"))
        command.extend(("--env", f"POSTGRES_PASSWORD={self.definition.password}"))
        command.extend(("--publish", f"{self.definition.port or 0}:5432", self.definition.image))
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        self._container_id = result.stdout.strip()
        port = self._published_port()
        self.outputs.host = self.definition.host
        self.outputs.port = port
        self.outputs.database = self.definition.database
        self.outputs.user = self.definition.user
        self.outputs.container_id = self._container_id
        self.outputs.dsn = (
            f"postgresql://{self.definition.user}:{self.definition.password}@"
            f"{self.definition.host}:{port}/{self.definition.database}"
        )
        logger.debug("Waiting for Postgres to accept connections")
        retry(self._connect, timeout=self.definition.timeout, interval=self.definition.interval)

    def teardown(self):
        if self._container_id and self.definition.delete_on_teardown:
            logger.debug("Removing Postgres container")
            subprocess.run(
                ["docker", "rm", "--force", self._container_id],
                check=False,
                text=True,
                capture_output=True,
            )

    def _published_port(self) -> int:
        result = subprocess.run(
            ["docker", "port", self._container_id, "5432/tcp"],
            check=True,
            text=True,
            capture_output=True,
        )
        return int(result.stdout.strip().rsplit(":", 1)[1])

    def _connect(self):
        with psycopg.connect(self.outputs.dsn):
            pass
