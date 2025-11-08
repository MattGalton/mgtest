import logging

import redis
from mgtest.api import TestInstance

logger = logging.getLogger(__name__)


class RedisQueryInstance(TestInstance):
    def run(self, resources):
        logger.debug("Executing Redis command %s", self.definition.command[0])
        client = redis.Redis.from_url(self.definition.url, decode_responses=True)
        try:
            value = client.execute_command(*self.definition.command)
        finally:
            client.close()
        self.outputs.value = value
        assert value == self.definition.expected, value
