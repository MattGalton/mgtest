"""NATS resources and tests for mgtest."""

from mgtest_nats.resources.nats_server.spec import NatsServer
from mgtest_nats.tests.nats_subscribe.spec import NatsSubscribe

__all__ = ["NatsServer", "NatsSubscribe"]
