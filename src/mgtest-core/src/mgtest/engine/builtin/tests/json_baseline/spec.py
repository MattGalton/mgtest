"""Definition for semantic JSON baseline comparisons."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.json_baseline.instance import JsonBaselineInstance


class JsonBaseline(TestSpec):
    """Compare a generated JSON document structurally with a checked-in baseline."""

    path: str | Path = Field(description="Generated JSON file to compare.")
    baseline: Path = Field(description="Checked-in JSON file used as the expected baseline.")

    class Output(BaseModel):
        """The JSON value read from the generated document."""

        document: Any | None = Field(
            default=None, description="JSON value read from the generated file."
        )

    def create_instance(self) -> JsonBaselineInstance:
        """Create the semantic JSON comparator."""
        return JsonBaselineInstance(self)
