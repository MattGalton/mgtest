from mgtest.api import ResourceSpec
from pydantic import BaseModel, Field

from mgtest_redis.resources.redis.instance import RedisInstance


class Redis(ResourceSpec):
    """Run an isolated Redis Docker container and expose its connection URL."""

    image: str = "redis:7-alpine"
    host: str = "127.0.0.1"
    port: int | None = Field(default=None, ge=1, le=65535)
    database: int = Field(default=0, ge=0)
    password: str | None = None
    docker_args: list[str] = Field(default_factory=list)
    timeout: float = Field(default=30.0, gt=0)
    interval: float = Field(default=0.1, gt=0)
    delete_on_teardown: bool = True

    class Output(BaseModel):
        host: str = ""
        port: int = 0
        database: int = 0
        url: str = ""
        container_id: str = ""

    def create_instance(self) -> RedisInstance:
        return RedisInstance(self)
