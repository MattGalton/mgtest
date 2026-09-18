from mgtest.api import ResourceSpec
from pydantic import BaseModel, Field

from mgtest_docker.resources.docker_container.instance import DockerContainerInstance


class DockerContainer(ResourceSpec):
    """A locally managed Docker container."""

    image: str
    command: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    ports: dict[int, int | None] = Field(default_factory=dict)
    docker_args: list[str] = Field(default_factory=list)

    class Output(BaseModel):
        container_id: str = ""
        ports: dict[int, int] = Field(default_factory=dict)

    def create_instance(self) -> DockerContainerInstance:
        return DockerContainerInstance(self)
