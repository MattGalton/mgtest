from __future__ import annotations

from abc import ABC, abstractmethod
from builtins import type as builtin_type
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpecBase(BaseModel, ABC):
    """Base class for all declarative definitions in the definitions"""

    # Override only when a stable YAML name must differ from the Python class name.
    TYPE: ClassVar[str | None] = None
    type: str = Field(..., description="The identifier for the resource/test")
    name: str = Field(
        ...,
        description=(
            "The name of the resource/test. This identifies it elsewhere and must be unique."
        ),
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def type_name(cls) -> str:
        return cls.TYPE or cls.__name__

    @classmethod
    def output_model(cls) -> builtin_type[BaseModel] | None:
        output = getattr(cls, "Output", None)
        return (
            output if isinstance(output, builtin_type) and issubclass(output, BaseModel) else None
        )

    @model_validator(mode="after")
    def _type_matches_class(self):
        if self.type != self.type_name():
            raise ValueError(f"Expected type '{self.type_name()}', got '{self.type}'")
        return self

    @abstractmethod
    def create_instance(self):
        """Return the instance associated with this definition"""
        raise NotImplementedError
