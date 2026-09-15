import json
import shutil
from pathlib import Path

from mgtest.tooling.schema.generator import SchemaGenerator


def write_vscode_settings(src_schemas_dir: Path, vscode_dir: Path):
    """Write schemas to .vscode/schemas and update .vscode/settings.json.
    Requires the YAML VSCode extension"""

    if vscode_dir.name != ".vscode":
        vscode_dir = vscode_dir / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    # Where the schemas will be copied into
    tgt_schemas_dir = vscode_dir / "mgtest_schemas"
    tgt_schemas_dir.mkdir(parents=True, exist_ok=True)

    # Copy src_schemas_dir to tgt_schemas_dir
    shutil.copytree(src_schemas_dir, tgt_schemas_dir, dirs_exist_ok=True)

    # Update settings.json
    settings_path = vscode_dir / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}

    # The vscode yaml extension demands every tooling be http or local, and local files MUST BE relative to .vscode
    test_top_level_path = (
        SchemaGenerator(tgt_schemas_dir)
        .test_top_level_path.relative_to(vscode_dir.parent)
        .as_posix()
    )
    resource_top_level_path = (
        SchemaGenerator(tgt_schemas_dir)
        .resource_top_level_path.relative_to(vscode_dir.parent)
        .as_posix()
    )

    yaml_schemas = settings.get("yaml.schemas", {})
    yaml_schemas.update(
        {str(test_top_level_path): "**/t_*.yml", str(resource_top_level_path): "**/r_*.yml"}
    )
    settings["yaml.schemas"] = yaml_schemas
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
