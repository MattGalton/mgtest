"""PostgreSQL resource and SQL checks for mgtest."""

from mgtest_sql.resources.postgres.spec import Postgres
from mgtest_sql.tests.sql_query.spec import SqlQuery

__all__ = ["Postgres", "SqlQuery"]
