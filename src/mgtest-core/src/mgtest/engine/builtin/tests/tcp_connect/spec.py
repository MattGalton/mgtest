from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.tcp_connect.instance import TcpConnectInstance


class TcpConnect(TestSpec):
    """Poll until a TCP server accepts a connection."""

    host: str = Field(description="Host name or address to connect to.")
    port: int = Field(ge=1, le=65535, description="TCP port that must accept a connection.")
    timeout: float = Field(default=10.0, gt=0, description="Maximum seconds to wait for a connection.")
    interval: float = Field(default=0.1, gt=0, description="Seconds between connection attempts.")

    class Output(BaseModel):
        connected: bool = Field(default=False, description="Whether a connection was established.")

    def create_instance(self) -> TcpConnectInstance:
        return TcpConnectInstance(self)
