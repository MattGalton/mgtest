import argparse
import json

import pytest
from mgtest.cli import mgtest_list, mgtest_run


def write_project(root):
    (root / "builtin" / "resources").mkdir(parents=True)
    (root / "builtin" / "resources" / "probe.py").write_text(
        "from pathlib import Path\n"
        "from mgtest.api.resource import ResourceInstance\n"
        "from mgtest.api.resource import ResourceSpec\n"
        "class ProbeInstance(ResourceInstance):\n"
        "    def setup(self):\n"
        "        Path(self.definition.log).open('a').write(\n"
        "            'start:' + self.definition.name + '\\n'\n"
        "        )\n"
        "    def teardown(self):\n"
        "        Path(self.definition.log).open('a').write(\n"
        "            'stop:' + self.definition.name + '\\n'\n"
        "        )\n"
        "class Probe(ResourceSpec):\n"
        "    log: str\n"
        "    def create_instance(self): return ProbeInstance(self)\n"
    )
    log = root / "resources.log"
    (root / "r_root.yaml").write_text(
        json.dumps({"type": "Probe", "name": "root", "log": str(log), "auto_start": True})
    )
    (root / "t_root.yaml").write_text(
        json.dumps({"type": "FileExists", "name": "root_check", "path": str(root)})
    )
    for suite in ("s_smoke", "s_other"):
        directory = root / suite
        directory.mkdir()
        if suite == "s_other":
            (directory / "r_other.yaml").write_text(
                json.dumps({"type": "Probe", "name": "other", "log": str(log), "auto_start": True})
            )
        (directory / f"t_{suite}.yaml").write_text(
            json.dumps({"type": "FileExists", "name": f"{suite}_check", "path": str(root)})
        )
    return log


def parse_args(arguments):
    parser = argparse.ArgumentParser()
    mgtest_run.populate_parser(parser)
    return parser.parse_args(arguments)


def manifest(root):
    run = next((root / ".mgtest" / "runs").iterdir())
    return json.loads((run / "manifest.json").read_text())


def test_run_selects_a_suite_and_starts_only_visible_resources(tmp_path):
    log = write_project(tmp_path)

    args = parse_args([str(tmp_path), "s_smoke"])
    assert args.func(args) == 0

    assert list(manifest(tmp_path)["tests"]) == ["s_smoke::tests.s_smoke_check"]
    assert log.read_text().splitlines() == ["start:root", "stop:root"]


def test_run_selects_one_qualified_test(tmp_path):
    write_project(tmp_path)
    args = parse_args([str(tmp_path), "s_smoke/s_smoke_check"])

    assert args.func(args) == 0
    assert list(manifest(tmp_path)["tests"]) == ["s_smoke::tests.s_smoke_check"]


def test_run_rejects_legacy_qualified_test_syntax(tmp_path):
    write_project(tmp_path)
    args = parse_args([str(tmp_path), "s_smoke::s_smoke_check"])

    with pytest.raises(ValueError, match="Unknown suite or test"):
        args.func(args)


def test_run_accepts_an_expected_failure(tmp_path):
    write_project(tmp_path)
    (tmp_path / "t_root.yaml").write_text(
        json.dumps(
            {
                "type": "FileExists",
                "name": "root_check",
                "path": str(tmp_path / "absent"),
                "expected_outcome": "failed",
            }
        )
    )

    args = parse_args([str(tmp_path)])

    assert args.func(args) == 0


def test_run_rejects_an_ambiguous_test_name(tmp_path):
    write_project(tmp_path)
    (tmp_path / "s_other" / "t_other.yaml").write_text(
        json.dumps({"type": "FileExists", "name": "s_smoke_check", "path": str(tmp_path)})
    )
    args = parse_args([str(tmp_path), "s_smoke_check"])

    with pytest.raises(ValueError, match="ambiguous"):
        args.func(args)


def test_list_displays_suites_and_tests(tmp_path, capsys):
    write_project(tmp_path)
    parser = argparse.ArgumentParser()
    mgtest_list.populate_parser(parser)
    args = parser.parse_args([str(tmp_path)])

    assert args.func(args) == 0
    assert capsys.readouterr().out.splitlines() == [
        ".",
        "  test root_check",
        "  s_other",
        "    test s_other_check",
        "  s_smoke",
        "    test s_smoke_check",
    ]
