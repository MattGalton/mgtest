from types import SimpleNamespace

from mgtest.engine.builtin.tests.port_available import instance as port_instance
from mgtest_sql.resources.postgres import instance as postgres_instance
from mgtest_sql.tests.sql_query import instance as query_instance


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


def docker_run(command, **_):
    if command[:3] == ["docker", "run", "--detach"]:
        return SimpleNamespace(stdout="postgres-fixture\n")
    if command[:2] == ["docker", "port"]:
        return SimpleNamespace(stdout="0.0.0.0:55432\n")
    return SimpleNamespace(stdout="")


class PortProbe:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def bind(self, address):
        assert address == ("127.0.0.1", 50123)


postgres_instance.subprocess = SimpleNamespace(run=docker_run)
postgres_instance.psycopg = SimpleNamespace(connect=lambda _dsn: Connection())
query_instance.psycopg = SimpleNamespace(connect=lambda _dsn: Connection())
port_instance.socket = SimpleNamespace(AF_INET=0, SOCK_STREAM=0, socket=lambda *_: PortProbe())
