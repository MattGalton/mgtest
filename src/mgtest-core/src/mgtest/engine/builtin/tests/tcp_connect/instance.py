from __future__ import annotations

import logging
import socket

from mgtest.api.test import TestInstance
from mgtest.engine.builtin.retry import retry

logger = logging.getLogger(__name__)


class TcpConnectInstance(TestInstance):
    def run(self, resources):
        logger.debug("Connecting to %s:%s", self.definition.host, self.definition.port)
        def connect():
            address = (self.definition.host, self.definition.port)
            with socket.create_connection(address, self.definition.interval):
                return True

        self.outputs.connected = retry(
            connect, timeout=self.definition.timeout, interval=self.definition.interval
        )
