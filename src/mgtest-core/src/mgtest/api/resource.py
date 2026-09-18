"""Public resource extension contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Literal

from pydantic import Field

from mgtest.api._definitions import SpecBase


class ResourceScope(StrEnum):
    """Controls how often a resource instance is created."""

    SUITE = "Suite"
    YAML_FILE = "File"
    TEST = "Test"

    @staticmethod
    def to_pytest(scope: ResourceScope) -> str:
        """Return the equivalent pytest fixture scope."""
        match scope:
            case ResourceScope.SUITE:
                return "module"
            case ResourceScope.YAML_FILE:
                return "class"
            case ResourceScope.TEST:
                return "function"
            case _:
                raise ValueError(f"Unknown resource scope {scope}")


class ResourceInstance(ABC):
    """Runtime implementation created from one resource definition."""

    def __init__(self, definition):
        self.definition = definition
        self._outputs = None

    def prepare(self) -> None:
        """Materialise durable local inputs without starting the resource."""
        return None

    @abstractmethod
    def setup(self) -> None:
        """Start or provision the resource."""
        ...

    @abstractmethod
    def teardown(self) -> None:
        """Stop the resource and release transient state."""
        ...

    def value(self):
        """Return the value passed to checks which require this resource."""
        return self

    @property
    def outputs(self):
        """Return structured outputs exposed through configuration references."""
        if self._outputs is None:
            output = self.definition.output_model()
            self._outputs = output() if output else {}
        return self._outputs

    def logs(self) -> str:
        """Return diagnostic logs to save with a failed run."""
        return ""


class ResourceSpec(SpecBase, ABC):
    """Declarative definition of a resource extension."""

    auto_start: bool = Field(
        False,
        description="Start before checks run, instead of on first usage",
    )
    scope: Literal[ResourceScope.SUITE, ResourceScope.YAML_FILE, ResourceScope.TEST] = Field(
        default=ResourceScope.SUITE,
        description=(
            "Suite shares one instance; File creates one instance per test YAML file; "
            "Test creates a fresh instance per check."
        ),
    )

    @abstractmethod
    def create_instance(self) -> ResourceInstance:
        """Create the runtime instance for this definition."""
        ...


__all__ = ["ResourceInstance", "ResourceScope", "ResourceSpec"]
