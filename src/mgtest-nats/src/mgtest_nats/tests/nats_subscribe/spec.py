from mgtest.api import TestSpec
from pydantic import BaseModel, Field

from mgtest_nats.tests.nats_subscribe.instance import NatsSubscribeInstance


class NatsSubscribe(TestSpec):
    """Wait for one NATS message on a subject and optionally assert its payload."""

    url: str = Field(description="NATS server connection URL.")
    subject: str = Field(description="Subject on which to wait for a message.")
    timeout: float = Field(default=10.0, gt=0, description="Maximum seconds to wait for a message.")
    payload: str | None = Field(default=None, description="Optional exact payload required for the message.")

    class Output(BaseModel):
        subject: str = Field(default="", description="Subject of the received message.")
        payload: str = Field(default="", description="Payload of the received message.")

    def create_instance(self) -> NatsSubscribeInstance:
        return NatsSubscribeInstance(self)
