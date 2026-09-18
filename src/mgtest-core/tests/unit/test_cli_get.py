import argparse
import json

import pytest
from mgtest.cli import mgtest_get


def _project(root):
    plugins = root / "builtin" / "resources"
    plugins.mkdir(parents=True)
    (plugins / "probe.py").write_text(
        "from pathlib import Path\n"
        "from mgtest.api import ResourceInstance, ResourceSpec\n"
        "class ProbeInstance(ResourceInstance):\n"
        "    def _log(self, phase): Path(self.definition.log).open('a').write(phase + '\\n')\n"
        "    def prepare(self): self._log('prepare')\n"
        "    def setup(self): self._log('start')\n"
        "    def teardown(self): self._log('stop')\n"
        "class Probe(ResourceSpec):\n"
        "    log: str\n"
        "    def create_instance(self): return ProbeInstance(self)\n"
    )
    log = root / "resource.log"
    (root / "r_probe.yaml").write_text(
        json.dumps({"type": "Probe", "name": "probe", "log": str(log), "auto_start": True})
    )
    suite = root / "s_smoke"
    suite.mkdir()
    (suite / "t_check.yaml").write_text(
        json.dumps({"type": "FileExists", "name": "check", "path": str(root)})
    )
    return log


def _args(arguments):
    parser = argparse.ArgumentParser()
    mgtest_get.populate_parser(parser)
    return parser.parse_args(arguments)


def test_get_prepares_resource_closure_and_writes_a_manifest(tmp_path, capsys):
    log = _project(tmp_path)
    args = _args([str(tmp_path), "s_smoke/check", "--prepare"])

    assert args.func(args) == 0
    workspace = next((tmp_path / ".mgtest" / "gets").iterdir())
    manifest = json.loads((workspace / "manifest.json").read_text())
    assert log.read_text().splitlines() == ["prepare"]
    assert manifest["get"]["target"] == "s_smoke::tests.check"
    assert manifest["get"]["resources"] == [".::resources.probe"]
    assert capsys.readouterr().out == f"Collected resources in {workspace}\n"


def test_get_command_starts_and_stops_resources(tmp_path):
    log = _project(tmp_path)
    args = _args([str(tmp_path), "s_smoke/check", "--command", 'test -n "$MGTEST_GET_DIR"'])

    assert args.func(args) == 0
    assert log.read_text().splitlines() == ["prepare", "start", "stop"]


def test_get_requires_explicit_opt_in_for_prerequisite_check_outputs(tmp_path):
    _project(tmp_path)
    suite = tmp_path / "s_smoke"
    (suite / "t_producer.yaml").write_text(
        json.dumps({"type": "FileExists", "name": "producer", "path": str(tmp_path)})
    )
    (suite / "t_check.yaml").write_text(
        json.dumps(
            {
                "type": "FileExists",
                "name": "check",
                "path": str(tmp_path),
                "depends_on": ["tests.producer"],
            }
        )
    )
    args = _args([str(tmp_path), "s_smoke/check"])

    with pytest.raises(ValueError, match="with-prerequisites"):
        args.func(args)
