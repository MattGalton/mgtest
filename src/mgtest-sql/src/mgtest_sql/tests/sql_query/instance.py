import logging

import psycopg
from mgtest.api import TestInstance

logger = logging.getLogger(__name__)


class SqlQueryInstance(TestInstance):
    def run(self, resources):
        logger.debug("Executing SQL query")
        with psycopg.connect(self.definition.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.definition.query, self.definition.parameters)
                rows = [list(row) for row in cursor.fetchall()] if cursor.description else []
        self.outputs.rows = rows
        self.outputs.row_count = len(rows)
        if self.definition.expected_row_count is not None:
            assert len(rows) == self.definition.expected_row_count, rows
        if self.definition.expected_scalar is not None:
            assert rows and rows[0], "Query returned no scalar value"
            assert rows[0][0] == self.definition.expected_scalar, rows
