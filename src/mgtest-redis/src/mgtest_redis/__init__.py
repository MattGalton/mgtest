"""Redis resource and checks for mgtest."""

from mgtest_redis.resources.redis.spec import Redis
from mgtest_redis.tests.redis_query.spec import RedisQuery

__all__ = ["Redis", "RedisQuery"]
