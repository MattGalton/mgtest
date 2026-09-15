import logging
from abc import ABC, abstractmethod
from enum import Enum

from pydantic import Field

from mgtest.internal.spec_base import SpecBase

logger = logging.getLogger(__name__)


class ResourceScope(Enum):
    """Allows overriding of resources setup/teardown frequency"""

    SUITE = "Suite"
    YAML_FILE = "File"
    TEST = "Test"

    @staticmethod
    def to_pytest(s: "ResourceScope") -> str:
        match s:
            case ResourceScope.SUITE:
                return "module"
            case ResourceScope.YAML_FILE:
                return "class"
            case ResourceScope.TEST:
                return "function"
            case _:
                raise Exception(f"Unknown resource scope {s}")


class ResourceSpec(SpecBase, ABC):
    auto_start: bool = Field(
        False,
        description="Automatically start the resource on collection, instead of on first usage",
    )
    scope: ResourceScope = Field(
        default=ResourceScope.SUITE,
        description="Determines how often this test is setup and torn down",
    )

    @abstractmethod
    def create_instance(self) -> "ResourceInstance":
        """Create an instance of the resource."""
        raise NotImplementedError
