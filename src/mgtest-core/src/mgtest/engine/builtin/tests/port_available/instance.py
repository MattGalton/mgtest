import logging
import socket

from mgtest.api.test import TestInstance

logger = logging.getLogger(__name__)


class PortAvailableInstance(TestInstance):
    def run(self, resources):
        logger.debug(
            "Checking whether %s:%s is available", self.definition.host, self.definition.port
        )
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((self.definition.host, self.definition.port))
        self.outputs.host = self.definition.host
        self.outputs.port = self.definition.port
        self.outputs.available = True
