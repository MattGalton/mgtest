import json

import pytest


def make_project(pytester, monkeypatch, scope="Suite"):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.delenv("MGT_PLUGIN_PATHS", raising=False)
    project = pytester.path / "mgtest"
    plugins = project / "builtin" / "resources"
    plugins.mkdir(parents=True)
    log = pytester.path / "lifecycle.txt"
    (plugins / "probe.py").write_text(
        "from pathlib import Path\n"
        "from mgtest.api.resource import ResourceSpec\n"
        "from mgtest.api.resource import ResourceInstance\n"
        "class ProbeInstance(ResourceInstance):\n"
        "    def setup(self):\n"
        "        with Path(self.definition.log).open('a') as f: f.write('start\\n')\n"
        "    def teardown(self):\n"
        "        with Path(self.definition.log).open('a') as f: f.write('stop\\n')\n"
        "class Probe(ResourceSpec):\n"
        "    log: str\n"
        "    def create_instance(self): return ProbeInstance(self)\n"
    )
    (project / "r_probe.yaml").write_text(json.dumps({
        "type": "Probe", "name": "probe", "log": str(log), "auto_start": True, "scope": scope,
    }))
    (project / "t_missing.yaml").write_text(
        json.dumps({"type": "FileExists", "name": "missing", "path": str(pytester.path / "absent")})
    )
    (project / "t_present.yaml").write_text(
        json.dumps({"type": "FileExists", "name": "present", "path": str(project)})
    )
    return project, log


@pytest.mark.parametrize("scope", ["Suite", "Test"])
def test_checks_report_individually_and_continue_after_failure(pytester, monkeypatch, scope):
    project, log = make_project(pytester, monkeypatch, scope)
    result = pytester.runpytest_subprocess("-p", "mgtest.engine.runner", "-v", "--tb=short")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*missing FAILED*", "*present PASSED*"])
    assert log.read_text().splitlines() == ["start", "stop"] * (2 if scope == "Test" else 1)
    failure = next((project / ".mgtest" / "runs").rglob("failure.txt"))
    assert "Path does not exist" in failure.read_text()


def test_check_can_be_selected_by_name(pytester, monkeypatch):
    project, log = make_project(pytester, monkeypatch)
    result = pytester.runpytest_subprocess("-p", "mgtest.engine.runner", "-k", "present", "-q")
    result.assert_outcomes(passed=1, deselected=1)
    assert log.read_text().splitlines() == ["start", "stop"]
    config = project / ".mgtest" / "config.yaml"
    runs = list((project / ".mgtest" / "runs").iterdir())
    assert "max_size_mb: 1024" in config.read_text()
    assert len(runs) == 1
    manifest = json.loads((runs[0] / "manifest.json").read_text())
    assert manifest["status"] == "passed"
    assert (runs[0] / "resolved-config.yaml").is_file()


def test_empty_configuration_fails_collection(pytester, monkeypatch):
    project, log = make_project(pytester, monkeypatch)
    (project / "t_missing.yaml").unlink()
    (project / "t_present.yaml").unlink()
    result = pytester.runpytest_subprocess("-p", "mgtest.engine.runner", "-q")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*No tests defined*"])
    assert not log.exists()


def test_expected_failure_is_reported_as_a_passing_expected_result(pytester, monkeypatch):
    project, _ = make_project(pytester, monkeypatch)
    (project / "t_missing.yaml").write_text(
        json.dumps(
            {
                "type": "FileExists",
                "name": "missing",
                "path": str(pytester.path / "absent"),
                "expected_outcome": "failed",
            }
        )
    )

    result = pytester.runpytest_subprocess("-p", "mgtest.engine.runner", "-q")

    result.assert_outcomes(passed=2)


def test_unexpected_pass_is_reported_as_a_failure(pytester, monkeypatch):
    project, _ = make_project(pytester, monkeypatch)
    (project / "t_missing.yaml").unlink()
    (project / "t_present.yaml").write_text(
        json.dumps(
            {
                "type": "FileExists",
                "name": "present",
                "path": str(project),
                "expected_outcome": "failed",
            }
        )
    )

    result = pytester.runpytest_subprocess("-p", "mgtest.engine.runner", "-q")

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*mgtest check passed unexpectedly*"])


def test_nested_suites_are_reflected_in_pytest_nodeids(pytester, monkeypatch):
    project, _ = make_project(pytester, monkeypatch)
    nested = project / "s_smoke" / "s_critical"
    nested.mkdir(parents=True)
    (nested / "t_nested.yaml").write_text(
        json.dumps(
            {
                "type": "FileExists",
                "name": "nested_check",
                "path": str(project),
            }
        )
    )

    result = pytester.runpytest_subprocess(
        "-p", "mgtest.engine.runner", "--collect-only", "-q"
    )

    result.stdout.fnmatch_lines(["*mgtest::s_smoke::s_critical::nested_check*"])
