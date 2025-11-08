import argparse
import json

from jsonschema import Draft202012Validator
from mgtest.cli import mgtest_schema
from mgtest.engine.plugin import PluginImporter
from mgtest.tooling.schema.generator import SchemaGenerator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


def test_definition_schemas_accept_project_documents(tmp_path):
    importer = PluginImporter()
    importer.load()
    generator = SchemaGenerator(tmp_path / "schemas", importer.catalog)
    generator.generate()
    registry = Registry()
    for path in generator.output_dir.rglob("*.json"):
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(
            path.as_uri(), Resource.from_contents(schema, default_specification=DRAFT202012)
        )
    schema = {"$ref": generator.test_top_level_path.as_uri()}
    validator = Draft202012Validator(schema, registry=registry)
    assert validator.is_valid({"type": "FileExists", "name": "exists", "path": "${vars.path}"})


def test_schema_cli_maps_root_config_files(tmp_path, monkeypatch):
    monkeypatch.delenv("MGT_PLUGIN_PATHS", raising=False)
    parser = mgtest_schema.populate_parser(argparse.ArgumentParser())
    output = tmp_path / "generated"
    args = parser.parse_args(["--output-dir", str(output), "--vscode", str(tmp_path)])
    assert mgtest_schema.run(args) == 0
    settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text())
    assert ["**/r_*.yml", "**/r_*.yaml"] in settings["yaml.schemas"].values()
    assert ["**/t_*.yml", "**/t_*.yaml"] in settings["yaml.schemas"].values()
