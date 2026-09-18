import json
import logging
import shutil
from pathlib import Path

from mgtest.engine.plugin.plugin_registries import PluginCatalog
from mgtest.engine.project.validation import authored_schema

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """Generate schemas for registered ``r_*.yaml`` and ``t_*.yaml`` definitions."""

    def __init__(self, output_dir: Path, catalog: PluginCatalog | None = None):
        self.output_dir = output_dir.resolve()
        self.catalog = catalog or PluginCatalog()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def test_top_level_path(self):
        return self.output_dir / "test.json"

    @property
    def resource_top_level_path(self):
        return self.output_dir / "resource.json"

    def clear(self):
        logger.debug("Clearing generated schemas in %s", self.output_dir)
        for plural in ("tests", "resources"):
            path = self.output_dir / plural
            if path.exists():
                shutil.rmtree(path)
        for path in (
            self.test_top_level_path,
            self.resource_top_level_path,
        ):
            path.unlink(missing_ok=True)

    def generate(self):
        logger.info("Generating schemas in %s", self.output_dir)
        self.clear()
        for singular, registry in (
            ("test", self.catalog.tests),
            ("resource", self.catalog.resources),
        ):
            plural = f"{singular}s"
            directory = self.output_dir / plural
            directory.mkdir(parents=True, exist_ok=True)
            references = []
            for index, cls in enumerate(registry.values()):
                # Index prefixes avoid collisions between plugins with equal class names.
                _, schema_text = self.generate_schema(cls)
                filename = f"{index}.json"
                (directory / filename).write_text(schema_text, encoding="utf-8")
                references.append({"$ref": f"{plural}/{filename}"})
            definition = {"oneOf": references} if references else {"not": {}}
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": singular,
                **definition,
            }
            (self.output_dir / f"{singular}.json").write_text(
                json.dumps(schema, indent=2) + "\n", encoding="utf-8"
            )
        logger.info("Generated schemas in %s", self.output_dir)

    @staticmethod
    def generate_schema(cls) -> tuple[str, str]:
        # Outputs are runtime values, never user-supplied configuration fields.
        schema = authored_schema(cls)
        return f"{cls.__name__}.json", json.dumps(schema, indent=2)
