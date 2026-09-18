from typing import Any

from mgtest.api import TestSpec
from pydantic import BaseModel, Field

from mgtest_redis.tests.redis_query.instance import RedisQueryInstance


class RedisQuery(TestSpec):
    """Execute a Redis command and assert that its returned value matches."""

    url: str = Field(description="Redis connection URL.")
    command: list[str | int | float] = Field(min_length=1, description="Redis command and its arguments.")
    expected: Any = Field(description="Value required from the Redis command.")

    class Output(BaseModel):
        value: Any = Field(default=None, description="Value returned by the Redis command.")

    def create_instance(self) -> RedisQueryInstance:
        return RedisQueryInstance(self)
