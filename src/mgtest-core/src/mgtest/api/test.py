"""Public check extension contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import Field, PrivateAttr

from mgtest.api._definitions import SpecBase


class TestInstance(ABC):
    """Runtime implementation created from one check definition."""

    def __init__(self, definition):
        self.definition = definition
        self._outputs = None

    @abstractmethod
    def run(self, resources) -> None:
        """Run the check against its visible resources."""
        ...

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


class TestSpec(SpecBase, ABC):
    """Declarative definition of a check extension."""

    expected_outcome: Literal["passed", "failed"] = Field(
        default="passed",
        description=(
            "The outcome expected from this check. A failed expectation is reported "
            "as an expected failure; a passing check with that expectation is an "
            "unexpected pass."
        ),
    )
    _source_path: Path | None = PrivateAttr(default=None)

    @property
    def source_path(self) -> Path:
        """Return the YAML document that defined this check."""
        if self._source_path is None:
            raise RuntimeError("The test definition has no source document")
        return self._source_path

    @source_path.setter
    def source_path(self, path: Path) -> None:
        """Associate this materialised definition with its YAML document."""
        self._source_path = path

    def validate_resources(self, resources) -> None:
        """Validate references before execution; extensions may override this hook."""

    @abstractmethod
    def create_instance(self) -> TestInstance:
        """Create the runtime instance for this definition."""
        ...


__all__ = ["TestInstance", "TestSpec"]
