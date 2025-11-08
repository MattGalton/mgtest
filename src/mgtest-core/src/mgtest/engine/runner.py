from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mgtest.engine.bootstrap import compile_project
from mgtest.engine.session import ExecutionSession
from mgtest.logging import TRACE_LEVEL, configured_level
from mgtest.runtime import RunWorkspace

logger = logging.getLogger(__name__)


def pytest_configure(config):
    if (level := configured_level()) is not None:
        logging.getLogger("mgtest").setLevel(level)


def _collect_checks(collector, project, suite):
    compiled = project.compiled
    for identity in compiled.test_order:
        definition = compiled.definitions[identity].definition
        if definition.suite != suite.id:
            continue
        yield MgtestCheck.from_parent(
            collector,
            name=definition.name,
            identity=identity,
            project=project,
        )


class MgtestSuite(pytest.Collector):
    """A pytest collector that mirrors one directory in an mgtest project."""

    def __init__(self, *, suite, project: MgtestProject, **kwargs):
        super().__init__(**kwargs)
        self.suite = suite
        self.project = project

    def collect(self):
        logger.log(TRACE_LEVEL, "Collecting suite %s", self.suite.id)
        yield from _collect_checks(self, self.project, self.suite)
        for child_id in sorted(self.suite.children):
            child = self.project.compiled.model.suites[child_id]
            yield MgtestSuite.from_parent(
                self,
                name=child.path.name,
                suite=child,
                project=self.project,
            )

    def teardown(self):
        logger.log(TRACE_LEVEL, "Tearing down pytest suite %s", self.suite.id)
        self.project.session.close_suite(self.suite.id)


class MgtestProject(pytest.Directory):
    def collect(self):
        root = Path(str(self.path))
        logger.log(logging.INFO, "Collecting mgtest project %s", root)
        self.compiled = compile_project(root)
        self.workspace = RunWorkspace.create(root, self.compiled)
        root_suite = self.compiled.model.suites["."]
        yield from _collect_checks(self, self, root_suite)
        for child_id in sorted(root_suite.children):
            child = self.compiled.model.suites[child_id]
            yield MgtestSuite.from_parent(self, name=child.path.name, suite=child, project=self)

    def setup(self):
        logger.log(TRACE_LEVEL, "Starting pytest execution session for %s", self.path)
        self.session = ExecutionSession(self.compiled, self.workspace)

    def teardown(self):
        try:
            self.session.teardown()
        finally:
            self.workspace.finalize()
            logger.log(TRACE_LEVEL, "Finalized pytest workspace %s", self.workspace.path)


class MgtestCheck(pytest.Item):
    def __init__(self, *, identity: str, project: MgtestProject, **kwargs):
        super().__init__(**kwargs)
        self.identity = identity
        self.project = project
        definition = project.compiled.definitions[identity].definition
        self.user_properties.extend(
            [
                ("mgtest.id", identity),
                ("mgtest.type", definition.data["type"]),
                ("mgtest.suite", definition.suite),
                ("mgtest.artifacts", str(project.workspace.path)),
            ]
        )
        if project.compiled.definitions[identity].expected_outcome == "failed":
            self.user_properties.append(("mgtest.expected_outcome", "failed"))

    def runtest(self):
        logger.log(TRACE_LEVEL, "Executing pytest check %s", self.identity)
        for dependency in self.project.compiled.test_dependencies(self.identity):
            if self.project.session.check_state(dependency).error is not None:
                pytest.skip(f"Prerequisite check failed: {dependency}")
        try:
            self.outputs = self.project.session.run_check(self.identity)
        except BaseException:
            assessment = self.project.session.check_state(self.identity).assessment
            if assessment is not None and assessment.matched:
                self.user_properties.append(("mgtest.actual_outcome", "failed"))
                self.user_properties.append(("mgtest.expectation", "matched"))
                logger.info("Accepted expected failure for pytest check %s", self.identity)
                return
            raise
        assessment = self.project.session.check_state(self.identity).assessment
        if assessment is not None and not assessment.matched:
            pytest.fail("mgtest check passed unexpectedly")

    def repr_failure(self, excinfo, style=None):
        return excinfo.getrepr(style=style or "short")

    def add_failure_artifacts(self):
        self.add_report_section(
            "call",
            "mgtest artifacts",
            f"Run artifacts: {self.project.workspace.path}\n"
            f"Check artifacts: {self.project.workspace.path / 'tests'}",
        )

    def reportinfo(self):
        definition = self.project.compiled.definitions[self.identity].definition
        return definition.source.path, definition.source.line - 1, f"mgtest check: {self.name}"


def pytest_collect_directory(parent, path):
    candidate = Path(str(path))
    if candidate.name == "mgtest" and not (candidate / "pyproject.toml").exists():
        return MgtestProject.from_parent(parent, path=path)
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if isinstance(item, MgtestCheck) and report.when == "call" and report.failed:
        item.add_failure_artifacts()
