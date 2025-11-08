import asyncio
import logging

import nats
from mgtest.api import TestInstance

logger = logging.getLogger(__name__)


class NatsSubscribeInstance(TestInstance):
    def run(self, resources):
        subject, payload = asyncio.run(self._receive())
        self.outputs.subject = subject
        self.outputs.payload = payload
        if self.definition.payload is not None:
            assert payload == self.definition.payload, payload

    async def _receive(self) -> tuple[str, str]:
        logger.debug("Subscribing to NATS subject %s", self.definition.subject)
        client = await nats.connect(self.definition.url, connect_timeout=self.definition.timeout)
        try:
            subscription = await client.subscribe(self.definition.subject)
            message = await subscription.next_msg(timeout=self.definition.timeout)
            return message.subject, message.data.decode()
        finally:
            await client.drain()
