from pydantic import BaseModel, ConfigDict, Field


class ResourceFile(BaseModel):
    """The model for a r_*.yml resources file. It can contain a single resource directly, or multiple resources if placed
    under a top-level "resources" array."""

    resources: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "ResourceFile":
        source = dict(data)
        if "resources" in source:
            resources = source["resources"]
        elif "resource" in source:
            resources = [source["resource"]]
        else:
            resources = [data]  # treat remaining YAML as a single resource

        return cls(resources=resources)
