from pydantic import BaseModel, ConfigDict, Field


class TestFile(BaseModel):
    """The model for a t_*.yml tests file. It can contain a single tests directly, or multiple tests if placed
    under a top-level "tests" array. We optionally allow the top-level "resources" array"""

    tests: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "TestFile":
        """
        Convert raw YAML dict into TestFileDefinition, inferring single or multiple tests
        """

        source = dict(data)
        if "tests" in source:
            tests_data = source["tests"]
        elif "test" in source:
            tests_data = [source["test"]]
        else:
            tests_data = [data]  # treat remaining YAML as a single test

        return cls(tests=tests_data)
