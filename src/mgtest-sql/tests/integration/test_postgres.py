from __future__ import annotations

import subprocess

from mgtest_sql.resources.postgres.spec import Postgres
from mgtest_sql.tests.sql_query.spec import SqlQuery


def test_postgres_resource_and_sql_query_use_the_reported_dsn(monkeypatch):
    from mgtest_sql.resources.postgres import instance as postgres_instance
    from mgtest_sql.tests.sql_query import instance as query_instance

    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        if command[:3] == ["docker", "run", "--detach"]:
            return subprocess.CompletedProcess(command, 0, "postgres-id\n", "")
        if command[:2] == ["docker", "port"]:
            return subprocess.CompletedProcess(command, 0, "0.0.0.0:55432\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    class Cursor:
        description = ("answer",)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def execute(self, query, parameters):
            assert query == "select %s"
            assert parameters == [42]

        def fetchall(self):
            return [(42,)]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(postgres_instance.subprocess, "run", run)
    monkeypatch.setattr(postgres_instance.psycopg, "connect", lambda dsn: Connection())
    monkeypatch.setattr(query_instance.psycopg, "connect", lambda dsn: Connection())
    resource = Postgres(
        type="Postgres", name="database", database="app", user="app", password="secret"
    ).create_instance()
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
    assert resource.outputs.port == 55432
    resource.teardown()
    assert commands[-1] == ["docker", "rm", "--force", "postgres-id"]
