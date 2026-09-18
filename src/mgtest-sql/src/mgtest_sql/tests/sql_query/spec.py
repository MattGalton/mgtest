from typing import Any

from mgtest.api import TestSpec
from pydantic import BaseModel, Field

from mgtest_sql.tests.sql_query.instance import SqlQueryInstance


class SqlQuery(TestSpec):
    """Execute a SQL query and assert its rows, row count, or scalar result."""

    dsn: str = Field(description="Database connection string.")
    query: str = Field(description="SQL statement to execute.")
    parameters: list[Any] = Field(default_factory=list, description="Positional parameters for the SQL statement.")
    expected_row_count: int | None = Field(default=None, ge=0, description="Required number of returned rows.")
    expected_scalar: Any | None = Field(default=None, description="Required first scalar value.")

    class Output(BaseModel):
        rows: list[list[Any]] = Field(default_factory=list, description="Rows returned by the query.")
        row_count: int = Field(default=0, description="Number of rows returned.")

    def create_instance(self) -> SqlQueryInstance:
        return SqlQueryInstance(self)
