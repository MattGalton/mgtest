import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from mgtest.engine.plugin.plugin_registries import PluginCatalog
from mgtest.engine.plugin.plugin_registry import PluginRegistry


class _Discriminator(BaseModel):
    propertyName: str
    mapping: dict[str, str]


class _TopLevelSchema(BaseModel):
    """Represents the top-level JSON tooling for tests/resources"""

    schema_: str = Field("https://json-schema.org/draft/2020-12/schema", alias="$schema")
    title: str
    oneOf: list[dict[str, str]] = Field(default_factory=list)
    discriminator: _Discriminator

    model_config = {
        "extra": "allow",
    }

    @classmethod
    def load(cls, path: Path):
        if path.exists():
            data = json.loads(path.read_text())
            return _TopLevelSchema.model_validate(data)
        return cls(
            title=path.stem, oneOf=[], discriminator=_Discriminator(propertyName="type", mapping={})
        )

    def add_definition(self, type_name: str, relative_path: str):
        """Add a new definition to the tooling if not already present"""
        if type_name not in self.discriminator.mapping:
            self.discriminator.mapping[type_name] = relative_path
            self.oneOf.append({"$ref": relative_path})


@dataclass
class _RegistryData:
    top_level_name: str  # The name of the top-level tooling
    definitions_dir: (
        Path  # Where the sub-schemas for this particular group of definitions will live
    )
    registry: PluginRegistry  # The group of definitions

    @property
    def top_level_path(self) -> Path:
        return self.definitions_dir.parent / f"{self.top_level_name}.json"


class SchemaGenerator:
    def __init__(self, output_dir: Path, catalog: PluginCatalog | None = None):
        self.output_dir = output_dir.resolve()
        self.catalog = catalog or PluginCatalog()
        self._test_registry_data = _RegistryData(
            top_level_name="test",
            definitions_dir=self.output_dir / "tests",
            registry=self.catalog.tests,
        )
        self._resource_registry_data = _RegistryData(
            top_level_name="resource",
            definitions_dir=self.output_dir / "resources",
            registry=self.catalog.resources,
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def test_top_level_path(self):
        return self._test_registry_data.top_level_path

    @property
    def resource_top_level_path(self):
        return self._resource_registry_data.top_level_path

    def generate(self):
        """Generate all schemas for tests and resources"""
        self.clear()
        self._write_schemas_for_registry(self._test_registry_data)
        self._write_schemas_for_registry(self._resource_registry_data)

    def clear(self):
        for path in (
            self._test_registry_data.definitions_dir,
            self._resource_registry_data.definitions_dir,
        ):
            if path.exists():
                shutil.rmtree(path)
        for path in (self.test_top_level_path, self.resource_top_level_path):
            path.unlink(missing_ok=True)

    def _write_schemas_for_registry(self, registry_data: _RegistryData):
        registry_data.definitions_dir.mkdir(parents=True, exist_ok=True)

        filename_to_schema_str: dict[str, str] = {}
        type_to_filepath: dict[str, str] = {}

        for cls in registry_data.registry.values():
            filename, schema_str = SchemaGenerator.generate_schema(cls)
            filename_to_schema_str[filename] = schema_str
            type_to_filepath[cls.TYPE] = str(
                (registry_data.definitions_dir / filename).relative_to(self.output_dir).as_posix()
            )

        # Write individual schemas
        for filename, schema_str in filename_to_schema_str.items():
            (registry_data.definitions_dir / filename).write_text(schema_str)

        # Write top-level tooling
        top_level_schema_path = registry_data.top_level_path
        top_level_schema = _TopLevelSchema.load(top_level_schema_path)
        for type_name, filepath in type_to_filepath.items():
            top_level_schema.add_definition(type_name, filepath)

        top_level_schema_path.write_text(top_level_schema.model_dump_json(by_alias=True, indent=2))

    @staticmethod
    def generate_schema(cls) -> tuple[str, str]:
        schema = cls.model_json_schema()
        if hasattr(cls, "Outputs") and issubclass(cls.Outputs, BaseModel):
            outputs_schema = cls.Outputs.model_json_schema()
            schema.setdefault("properties", {})["outputs"] = outputs_schema
        filename = f"{schema.get('title', cls.TYPE)}.json"
        return filename, json.dumps(schema, indent=2)
