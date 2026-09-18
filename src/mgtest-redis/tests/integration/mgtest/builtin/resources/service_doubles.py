from types import SimpleNamespace

from mgtest_redis.resources.redis import instance as redis_instance
from mgtest_redis.tests.redis_query import instance as redis_query_instance


def docker_run(command, **_):
    if command[:3] == ["docker", "run", "--detach"]:
        return SimpleNamespace(stdout="redis-fixture\n")
    if command[:2] == ["docker", "port"]:
        return SimpleNamespace(stdout="0.0.0.0:56379\n")
    return SimpleNamespace(stdout="")


class RedisProbe:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class RedisClient:
    def execute_command(self, *command):
        assert command == ("GET", "answer")
        return "42"

    def close(self):
        pass


redis_instance.subprocess = SimpleNamespace(run=docker_run)
redis_instance.socket = SimpleNamespace(create_connection=lambda *_args, **_kwargs: RedisProbe())
redis_query_instance.redis = SimpleNamespace(
    Redis=SimpleNamespace(from_url=lambda *_args, **_kwargs: RedisClient())
)
