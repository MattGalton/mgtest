"""Opt-in coverage for the integrations against their real external systems."""

import os
import socket
import time
import uuid

import pytest
from mgtest_docker import DockerContainer
from mgtest_redis import Redis, RedisQuery
from mgtest_s3 import S3Bucket, S3Object, S3ObjectExists, S3ObjectMatches
from mgtest_sql import Postgres, SqlQuery


def _wait_for_port(port: int, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)


@pytest.mark.real_integration
def test_docker_container_runs_a_real_service():
    container = DockerContainer(
        type="DockerContainer",
        name="web",
        image="nginx:1.27-alpine",
        ports={80: None},
    ).create_instance()
    try:
        container.setup()
        port = container.outputs.ports[80]
        _wait_for_port(port)
        assert isinstance(container.logs(), str)
    finally:
        container.teardown()


@pytest.mark.real_integration
def test_redis_resource_and_query_use_a_real_redis_server():
    resource = Redis(type="Redis", name="cache").create_instance()
    try:
        resource.setup()
        query = RedisQuery(
            type="RedisQuery",
            name="ping",
            url=resource.outputs.url,
            command=["PING"],
            expected="PONG",
        ).create_instance()
        query.run({})
        assert query.outputs.value == "PONG"
    finally:
        resource.teardown()


@pytest.mark.real_integration
def test_postgres_resource_and_query_use_a_real_postgres_server():
    resource = Postgres(
        type="Postgres",
        name="database",
        database="integration",
        user="integration",
        password="integration-password",
    ).create_instance()
    try:
        resource.setup()
        query = SqlQuery(
            type="SqlQuery",
            name="answer",
            dsn=resource.outputs.dsn,
            query="select %s",
            parameters=[42],
            expected_scalar=42,
        ).create_instance()
        query.run({})
        assert query.outputs.rows == [[42]]
    finally:
        resource.teardown()


@pytest.mark.real_integration
def test_s3_resources_and_checks_use_a_real_s3_compatible_service():
    endpoint_url = os.environ["MGT_REAL_S3_ENDPOINT"]
    bucket_name = f"mgtest-real-{uuid.uuid4().hex}"
    bucket = S3Bucket(
        type="S3Bucket", name="bucket", bucket=bucket_name, endpoint_url=endpoint_url
    ).create_instance()
    obj = S3Object(
        type="S3Object",
        name="object",
        bucket=bucket_name,
        key="status.txt",
        body="ready",
        endpoint_url=endpoint_url,
    ).create_instance()
    try:
        bucket.setup()
        obj.setup()
        exists = S3ObjectExists(
            type="S3ObjectExists",
            name="exists",
            bucket=bucket_name,
            key="status.txt",
            endpoint_url=endpoint_url,
        ).create_instance()
        matches = S3ObjectMatches(
            type="S3ObjectMatches",
            name="matches",
            bucket=bucket_name,
            key="status.txt",
            equals="ready",
            endpoint_url=endpoint_url,
        ).create_instance()
        exists.run({})
        matches.run({})
        assert exists.outputs.exists is True
        assert matches.outputs.content == "ready"
    finally:
        obj.teardown()
        bucket.teardown()
