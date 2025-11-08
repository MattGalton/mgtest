from pathlib import Path

from mgtest.api import ResourceSpec
from pydantic import BaseModel, Field

from mgtest_docker.resources.docker_compose.instance import DockerComposeInstance


class DockerCompose(ResourceSpec):
    """Start selected services from a Docker Compose project and tear them down."""

    files: list[Path] = Field(default_factory=lambda: [Path("compose.yaml")])
    project_name: str | None = None
    working_directory: Path | None = None
    services: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    remove_volumes: bool = True

    class Output(BaseModel):
        containers: list[str] = Field(default_factory=list)

    def create_instance(self) -> DockerComposeInstance:
        return DockerComposeInstance(self)
