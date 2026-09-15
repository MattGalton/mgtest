import json
import sys

import pytest
from pydantic import ValidationError

from mgtest.engine import Engine, RunRequest, YamlConfigurationProvider
from mgtest.engine.plugin import PluginImporter


def make_engine():
    importer = PluginImporter()
    assert importer.load() >= 3
    return Engine(importer.catalog)


def test_yaml_vertical_slice(tmp_path):
    (tmp_path / "r_python.yml").write_text(
        json.dumps(
            {
                "type": "Executable",
                "name": "python",
                "path": sys.executable,
                "args": ["-u", "-c", "print('Hello World')"],
            }
        )
    )
    (tmp_path / "t_output.yml").write_text(
        json.dumps(
            {
                "type": "StreamRegex",
                "name": "output",
                "resource": "python",
                "pattern": "Hello World",
            }
        )
    )
    engine = make_engine()
    plan = engine.plan(YamlConfigurationProvider(), RunRequest(tmp_path))
    results = engine.run(plan)
    assert results[0].found is True


def test_unknown_fields_are_rejected(tmp_path):
    (tmp_path / "t_bad.yml").write_text(
        "type: FileExists\nname: bad\npath: somewhere\ntypo: true\n"
    )
    with pytest.raises(ValidationError):
        make_engine().plan(YamlConfigurationProvider(), RunRequest(tmp_path))


def test_yaml_loading_does_not_mutate_input():
    from mgtest.engine.config.resource_file import ResourceFile

    data = {"resource": {"type": "Anything"}}
    ResourceFile.from_yaml_dict(data)
    assert data == {"resource": {"type": "Anything"}}
