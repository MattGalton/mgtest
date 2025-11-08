from mgtest.api import ResourceSpec
from pydantic import BaseModel, Field

from mgtest_sql.resources.postgres.instance import PostgresInstance


class Postgres(ResourceSpec):
    """Run an isolated PostgreSQL Docker container and expose its DSN."""

    image: str = "postgres:16-alpine"
    database: str = "postgres"
    user: str = "postgres"
    password: str = "postgres"
    host: str = "127.0.0.1"
    port: int | None = Field(default=None, ge=1, le=65535)
    docker_args: list[str] = Field(default_factory=list)
    timeout: float = Field(default=30.0, gt=0)
    interval: float = Field(default=0.1, gt=0)
    delete_on_teardown: bool = True

    class Output(BaseModel):
        host: str = ""
        port: int = 0
        database: str = ""
        user: str = ""
        dsn: str = ""
        container_id: str = ""

    def create_instance(self) -> PostgresInstance:
        return PostgresInstance(self)
