import logging
from types import SimpleNamespace

import pytest
from mgtest.api.events import LifecycleEvent
from mgtest.api.resource import ResourceInstance
from mgtest.api.test import TestInstance
from mgtest.engine.session import _log_event
from mgtest.logging import TRACE_LEVEL, configured_level
from mgtest.runtime.cache import CacheStore
from mgtest.runtime.runs import RunWorkspace


def test_lifecycle_events_are_quiet_at_warning_and_report_failures(caplog):
    caplog.set_level(logging.WARNING, logger="mgtest")
    _log_event(LifecycleEvent("test", "run", "started", "check", "Probe", "quiet"))
    assert not caplog.records

    caplog.set_level("INFO", logger="mgtest")
    _log_event(LifecycleEvent("test", "run", "started", "check", "Probe", "broken"))
    _log_event(
        LifecycleEvent("test", "run", "failed", "check", "Probe", "broken", AssertionError())
    )
    assert [record.getMessage() for record in caplog.records] == [
        "Running Probe test 'broken'",
        "Failed Probe test 'broken'",
    ]
    assert [record.levelname for record in caplog.records] == ["INFO", "ERROR"]


def test_expected_test_failure_is_an_informational_lifecycle_event(caplog):
    caplog.set_level("INFO", logger="mgtest")

    _log_event(
        LifecycleEvent(
            "test", "run", "expected_failed", "check", "Probe", "known_issue", AssertionError()
        )
    )

    assert [record.getMessage() for record in caplog.records] == [
        "Failed as expected Probe test 'known_issue'"
    ]
    assert [record.levelname for record in caplog.records] == ["INFO"]


def test_instances_are_plain_extension_code_and_session_events_log_lifecycle(caplog):
    events = []

    class LoggedResource(ResourceInstance):
        def setup(self):
            events.append("setup")

        def teardown(self):
            events.append("teardown")

    class LoggedTest(TestInstance):
        def run(self, resources):
            events.append("run")

    definition = SimpleNamespace(type="Probe", name="example", output_model=lambda: None)
    caplog.set_level("INFO")
    resource_instance = LoggedResource(definition)
    resource_instance.setup()
    LoggedTest(definition).run({})
    assert events == ["setup", "run"]
    assert not caplog.records

    _log_event(LifecycleEvent("resource", "setup", "started", "resource", "Probe", "example"))
    _log_event(LifecycleEvent("resource", "setup", "passed", "resource", "Probe", "example"))
    _log_event(LifecycleEvent("test", "run", "started", "test", "Probe", "example"))
    _log_event(LifecycleEvent("test", "run", "passed", "test", "Probe", "example"))
    assert [record.getMessage() for record in caplog.records] == [
        "Setting up Probe resource 'example'",
        "Ready Probe resource 'example'",
        "Running Probe test 'example'",
        "Passed Probe test 'example'",
    ]

    caplog.set_level(TRACE_LEVEL, logger="mgtest")
    resource_instance.teardown()
    _log_event(LifecycleEvent("resource", "teardown", "started", "resource", "Probe", "example"))
    _log_event(LifecycleEvent("resource", "teardown", "passed", "resource", "Probe", "example"))
    assert [record.getMessage() for record in caplog.records[-2:]] == [
        "Tearing down Probe resource 'example'",
        "Stopped Probe resource 'example'",
    ]
    assert events == ["setup", "run", "teardown"]


def test_log_level_can_be_selected_with_an_environment_variable(monkeypatch):
    monkeypatch.setenv("MGT_LOG_LEVEL", "debug")
    assert configured_level() == 10
    monkeypatch.setenv("MGT_LOG_LEVEL", "verbose")
    with pytest.raises(ValueError, match="MGT_LOG_LEVEL"):
        configured_level()


def test_workspace_reports_resource_and_test_logs_for_failures(tmp_path, caplog):
    workspace = RunWorkspace(tmp_path, "run", CacheStore(tmp_path / "cache", 1))
    resource = SimpleNamespace(logs=lambda: "database diagnostics")
    test = SimpleNamespace(logs=lambda: "assertion diagnostics")
    caplog.set_level("ERROR")
    workspace.resource("suite::resources.database", instance=resource, error=RuntimeError("setup"))
    workspace.test("suite::tests.check", instance=test, error=AssertionError("check"))
    resource_logs = workspace.path / "resources" / "suite__resources.database" / "logs.txt"
    assert resource_logs.read_text() == ("database diagnostics")
    assert (workspace.path / "tests" / "suite__tests.check" / "logs.txt").read_text() == (
        "assertion diagnostics"
    )
