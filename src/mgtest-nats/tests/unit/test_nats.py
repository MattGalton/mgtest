from mgtest_nats.resources.nats_server.spec import NatsServer
from mgtest_nats.tests.nats_subscribe.spec import NatsSubscribe


def test_nats_definitions_expose_documented_outputs():
    server = NatsServer(name="nats", type="NatsServer")
    check = NatsSubscribe(
        name="event", type="NatsSubscribe", url="nats://127.0.0.1:4222", subject="events"
    )

    assert server.output_model()().url == ""
    assert check.output_model()().subject == ""
    assert NatsServer.__doc__
    assert NatsSubscribe.__doc__
