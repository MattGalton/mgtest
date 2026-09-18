from mgtest.api import ResourceSpec
from pydantic import BaseModel, Field

from mgtest_nats.resources.nats_server.instance import NatsServerInstance


class NatsServer(ResourceSpec):
    """Run a local ``nats-server`` process and expose its client URL."""

    executable: str = "nats-server"
    host: str = "127.0.0.1"
    port: int = Field(default=4222, ge=1, le=65535)
    args: list[str] = Field(default_factory=list)
    timeout: float = Field(default=10.0, gt=0)
    interval: float = Field(default=0.1, gt=0)

    class Output(BaseModel):
        host: str = ""
        port: int = 0
        url: str = ""

    def create_instance(self) -> NatsServerInstance:
        return NatsServerInstance(self)
