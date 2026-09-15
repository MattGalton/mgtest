from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpecBase(BaseModel, ABC):
    """Base class for all declarative definitions in the definitions"""

    class Inputs(BaseModel):
        """Abstract inputs class. Subclasses should override this."""

        pass

    class Outputs(BaseModel):
        """Abstract outputs class. Subclasses should override this."""

        pass

    # Code-level identity of your definition. You MUST change this.
    # e.g TYPE = "DockerContainer"
    TYPE: ClassVar[str] = "__CHANGE_ME__"
    type: str = Field(..., description="The identifier for the resource/test")
    name: str = Field(
        ...,
        description="The name of the resource/test. This is how you identify the resource elsewhere. It must be unique",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _type_matches_class(self):
        if self.type != self.TYPE:
            raise ValueError(f"Expected type '{self.TYPE}', got '{self.type}'")
        return self

    @abstractmethod
    def create_instance(self):
        """Return the instance associated with this definition"""
        raise NotImplementedError
