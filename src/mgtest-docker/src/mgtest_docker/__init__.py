"""Docker-backed resources for mgtest."""

from mgtest_docker.resources.docker_compose.spec import DockerCompose
from mgtest_docker.resources.docker_container.spec import DockerContainer

__all__ = ["DockerCompose", "DockerContainer"]
