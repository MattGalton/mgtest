import logging
import socket
import subprocess

from mgtest.api import ResourceInstance, retry

logger = logging.getLogger(__name__)


class NatsServerInstance(ResourceInstance):
    def setup(self):
        command = [
            self.definition.executable,
            "--addr",
            self.definition.host,
            "--port",
            str(self.definition.port),
        ]
        command.extend(self.definition.args)
        logger.debug("Starting NATS server: %s", command)
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        retry(self._connect, timeout=self.definition.timeout, interval=self.definition.interval)
        self.outputs.host = self.definition.host
        self.outputs.port = self.definition.port
        self.outputs.url = f"nats://{self.definition.host}:{self.definition.port}"

    def teardown(self):
        if hasattr(self, "process") and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=self.definition.timeout)

    def logs(self) -> str:
        if not hasattr(self, "process") or self.process.stdout is None:
            return ""
        return self.process.stdout.read().decode(errors="replace")

    def _connect(self):
        with socket.create_connection(
            (self.definition.host, self.definition.port), self.definition.interval
        ):
            pass
