from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.port_available.instance import PortAvailableInstance


class PortAvailable(TestSpec):
    """Assert that a TCP port is available for a process to bind."""

    host: str = Field(default="127.0.0.1", description="Interface on which to test port availability.")
    port: int = Field(ge=1, le=65535, description="TCP port that must be available to bind.")

    class Output(BaseModel):
        host: str = Field(default="", description="Host that was tested.")
        port: int = Field(default=0, description="Port that was tested.")
        available: bool = Field(default=False, description="Whether the port was available.")

    def create_instance(self) -> PortAvailableInstance:
        return PortAvailableInstance(self)
