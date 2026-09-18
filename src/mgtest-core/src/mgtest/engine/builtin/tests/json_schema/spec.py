from typing import Any

from pydantic import BaseModel, Field

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.json_schema.instance import JsonSchemaInstance


class JsonSchema(TestSpec):
    """Validate an in-memory JSON value against a JSON Schema document."""

    document: Any = Field(description="JSON-compatible value to validate.")
    json_schema: dict[str, Any] = Field(alias="schema", description="JSON Schema used to validate the document.")

    class Output(BaseModel):
        document: Any | None = Field(default=None, description="Document that was validated.")

    def create_instance(self) -> JsonSchemaInstance:
        return JsonSchemaInstance(self)
