"""The lifecycle authority for one compiled mgtest project."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from mgtest.api.events import ExecutionOutcome, LifecycleEvent, LifecycleListener
from mgtest.api.resource import ResourceInstance, ResourceScope
from mgtest.engine.outcomes import OutcomeAssessment, assess_outcome
from mgtest.engine.project.compiler import CompiledTest
from mgtest.engine.project.model import ProjectError
from mgtest.engine.project.references import get_path
from mgtest.logging import TRACE_LEVEL
from mgtest.runtime import NullWorkspace

logger = logging.getLogger(__name__)


class UnexpectedOutcome(AssertionError):
    """A check completed, but its actual result differs from its expectation."""


def _log_event(event: LifecycleEvent) -> None:
    """Render lifecycle events as useful normal mgtest logs."""
    action = {
        ("resource", "setup", "started"): "Setting up",
        ("resource", "setup", "passed"): "Ready",
        ("resource", "setup", "failed"): "Failed to set up",
        ("resource", "teardown", "started"): "Tearing down",
        ("resource", "teardown", "passed"): "Stopped",
        ("resource", "teardown", "failed"): "Failed to tear down",
        ("test", "run", "started"): "Running",
        ("test", "run", "passed"): "Passed",
        ("test", "run", "failed"): "Failed",
        ("test", "run", "expected_failed"): "Failed as expected",
    }[event.kind, event.phase, event.status]
    level = (
        logging.ERROR
        if event.status == "failed"
        else (TRACE_LEVEL if event.phase == "teardown" else logging.INFO)
    )
    logger.log(level, "%s %s %s '%s'", action, event.type_name, event.kind, event.name)


@dataclass
class ResourceState:
    """All mutable lifecycle facts for one resource identity."""

    instance: ResourceInstance | None = None
    prepared: bool = False
    started: bool = False
    error: BaseException | None = None
    outcome: ExecutionOutcome | None = None


@dataclass
class CheckState:
    """All mutable execution facts for one test identity."""

    result: object | None = None
    error: BaseException | None = None
    outcome: ExecutionOutcome | None = None
    assessment: OutcomeAssessment | None = None


class ScopeCoordinator:
    """Apply Test, File, and Suite resource boundaries for one session."""

    def __init__(self, session: ExecutionSession):
        self.session = session
        self.test_file: Path | None = None

    def before_check(self, node: CompiledTest) -> None:
        """Close File-scoped resources when moving to another YAML document."""
        path = node.definition.source.path
        if self.test_file is not None and self.test_file != path:
            logger.debug("Changing test file from %s to %s", self.test_file, path)
            self.session._teardown_scope(ResourceScope.YAML_FILE)
        self.test_file = path

    def after_check(self) -> None:
        """Close resources whose lifetime is one check."""
        self.session._teardown_scope(ResourceScope.TEST)

    def enter_suite(self, suite: str) -> None:
        """Close resource suites that are no longer ancestors of the next check."""
        self.session._teardown_outside_suite(suite)

    def close_suite(self, suite: str) -> None:
        """Close resources belonging to a pytest collector that has finished."""
        self.session._teardown_suite(suite)

    def finish(self) -> None:
        """Close every started resource in reverse setup order."""
        self.session._teardown_all()


class ResourceView(Mapping):
    """A test's visible resource namespace."""

    def __init__(self, session: ExecutionSession, suite: str):
        self.session = session
        self.suite = suite
        self.names = session.project.model.visible(suite, "resources")

    def required(self, name):
        """Start and return one named visible resource."""
        if name not in self.names:
            raise KeyError(f"Unknown resource '{name}'. Available: {sorted(self.names)}")
        return self.session.start_resource(self.names[name]).value()

    def __getitem__(self, name):
        return self.required(name)

    def __iter__(self):
        return iter(self.names)

    def __len__(self):
        return len(self.names)


class ExecutionSession:
    """One execution of a compiled snapshot, shared by CLI and pytest adapters."""

    def __init__(self, project, workspace=None, listeners: tuple[LifecycleListener, ...] = ()):
        self.project = project
        self.workspace = workspace or NullWorkspace()
        self.resource_states = {identity: ResourceState() for identity in project.resources}
        self.check_states = {identity: CheckState() for identity in project.tests}
        self.started_resources: list[str] = []
        self.listeners = (_log_event, *listeners)
        self.scopes = ScopeCoordinator(self)

    @property
    def instances(self):
        """Compatibility view of started resource instances."""
        return {
            identity: state.instance
            for identity, state in self.resource_states.items()
            if state.started and state.instance is not None
        }

    @property
    def prepared(self):
        """Compatibility view of prepared resource instances."""
        return {
            identity: state.instance
            for identity, state in self.resource_states.items()
            if state.prepared and state.instance is not None
        }

    @property
    def resource_errors(self):
        return {
            identity: state.error
            for identity, state in self.resource_states.items()
            if state.error is not None
        }

    @property
    def results(self):
        return {
            identity: state.result
            for identity, state in self.check_states.items()
            if state.outcome is not None and state.outcome.status == "passed"
        }

    @property
    def test_errors(self):
        return {
            identity: state.error
            for identity, state in self.check_states.items()
            if state.error is not None
        }

    @property
    def outcomes(self):
        return {
            **{
                identity: state.outcome
                for identity, state in self.resource_states.items()
                if state.outcome is not None
            },
            **{
                identity: state.outcome
                for identity, state in self.check_states.items()
                if state.outcome is not None
            },
        }

    def check_state(self, identity: str) -> CheckState:
        """Return one check's state record."""
        self.project.test(identity)
        return self.check_states[identity]

    def emit(self, event: LifecycleEvent) -> None:
        """Publish a lifecycle transition to adapters without changing execution."""
        for listener in self.listeners:
            listener(event)

    def _event(self, identity, kind, phase, status, error=None) -> LifecycleEvent:
        definition = self.project.definitions[identity].definition
        return LifecycleEvent(
            kind=kind,
            phase=phase,
            status=status,
            identity=identity,
            type_name=definition.data["type"],
            name=definition.name,
            error=error,
        )

    def output(self, reference):
        """Resolve one runtime output reference through the typed project node."""
        if reference.target in self.project.resources:
            outputs = self.start_resource(reference.target).outputs
        else:
            outputs = self.run_check(reference.target)
        try:
            return get_path(outputs, reference.path)
        except (KeyError, IndexError, AttributeError, TypeError) as error:
            raise ProjectError(
                f"Output unavailable: {reference.target}.{'.'.join(reference.path)}",
                reference.source,
            ) from error

    def start_resource(self, identity: str):
        """Start a resource once, including all resource prerequisites."""
        node = self.project.resource(identity)
        state = self.resource_states[identity]
        if state.error is not None:
            raise RuntimeError(f"Resource '{identity}' previously failed setup") from state.error
        if state.started:
            logger.log(TRACE_LEVEL, "Reusing resource %s", identity)
            return state.instance
        instance = state.instance if state.prepared else None
        try:
            self.emit(self._event(identity, "resource", "setup", "started"))
            for dependency in self.project.resource_dependencies(identity):
                self.start_resource(dependency)
            if instance is None:
                instance = node.materialize(self.output).create_instance()
            with self.workspace.active():
                instance.setup()
        except BaseException as error:
            error.add_note(f"Resource {identity} at {node.definition.source}")
            state.error = error
            state.outcome = ExecutionOutcome("resource", identity, "failed", error=error)
            self.emit(self._event(identity, "resource", "setup", "failed", error))
            self.workspace.resource(identity, instance=instance, error=error)
            if instance is not None:
                self._cleanup_failed_resource(identity, instance, error)
            raise
        state.instance = instance
        state.prepared = False
        state.started = True
        state.outcome = ExecutionOutcome("resource", identity, "passed", instance)
        self.started_resources.append(identity)
        self.emit(self._event(identity, "resource", "setup", "passed"))
        self.workspace.resource(identity, instance=instance)
        return instance

    def _cleanup_failed_resource(self, identity, instance, error) -> None:
        try:
            instance.teardown()
        except BaseException as cleanup_error:
            logger.error(
                "Resource cleanup after failed setup also failed: %s (%s)", identity, cleanup_error
            )
            raise BaseExceptionGroup(
                "Resource setup and cleanup failed", [error, cleanup_error]
            ) from None

    def prepare_resource(self, identity: str):
        """Materialise local resource inputs without starting their runtime process."""
        node = self.project.resource(identity)
        state = self.resource_states[identity]
        if state.started or state.prepared:
            return state.instance
        try:
            for dependency in self.project.resource_dependencies(identity):
                self.prepare_resource(dependency)
            instance = node.materialize(self.output).create_instance()
            with self.workspace.active():
                instance.prepare()
        except BaseException as error:
            error.add_note(f"Resource preparation {identity} at {node.definition.source}")
            state.error = error
            self.workspace.resource(identity, instance=locals().get("instance"), error=error)
            raise
        state.instance = instance
        state.prepared = True
        self.workspace.resource(identity, instance=instance)
        return instance

    def collect(self, test_id: str, *, start: bool = False, with_prerequisites: bool = False):
        """Collect resources required for a check and optionally keep them running."""
        resources, prerequisite_tests = self.project.requirements_for(test_id)
        if prerequisite_tests and not with_prerequisites:
            required = ", ".join(prerequisite_tests)
            raise ValueError(
                f"{test_id} requires check outputs from {required}; pass --with-prerequisites"
            )
        if with_prerequisites:
            for prerequisite in prerequisite_tests:
                self.run_check(prerequisite)
        for identity in resources:
            self.prepare_resource(identity)
        if start:
            for identity in resources:
                self.start_resource(identity)
        return resources, prerequisite_tests

    def run_check(self, identity: str):
        """Run a check once and retain its actual outcome before raising failures."""
        node = self.project.test(identity)
        state = self.check_states[identity]
        if state.error is not None:
            raise RuntimeError(f"Prerequisite test '{identity}' failed") from state.error
        if state.outcome is not None and state.outcome.status == "passed":
            logger.log(TRACE_LEVEL, "Reusing result for check %s", identity)
            return state.result
        self.scopes.before_check(node)
        instance = None
        try:
            self.emit(self._event(identity, "test", "run", "started"))
            for dependency in self.project.test_dependencies(identity):
                self.run_check(dependency)
            resources = ResourceView(self, node.definition.suite)
            for target in resources.names.values():
                if self.project.resource(target).auto_start:
                    self.start_resource(target)
            for dependency in self.project.resource_dependencies(identity):
                self.start_resource(dependency)
            instance = node.materialize(self.output).create_instance()
            instance.run(resources)
            result = instance.outputs
        except BaseException as error:
            error.add_note(f"Check {identity} at {node.definition.source}")
            state.error = error
            state.assessment = assess_outcome(node.expected_outcome, "failed")
            state.outcome = ExecutionOutcome("test", identity, "failed", error=error)
            self.emit(
                self._event(identity, "test", "run", state.assessment.lifecycle_status, error)
            )
            self.workspace.test(identity, instance=instance, error=error)
            self.capture_resource_logs()
            self._finish_check_after_failure(error)
            raise
        try:
            self.scopes.after_check()
        except BaseException as error:
            state.error = error
            state.assessment = assess_outcome(node.expected_outcome, "failed")
            state.outcome = ExecutionOutcome("test", identity, "failed", error=error)
            logger.error("Check cleanup failed: %s (%s)", identity, error)
            self.workspace.test(identity, instance=instance, error=error)
            raise
        state.result = result
        state.assessment = assess_outcome(node.expected_outcome, "passed")
        state.outcome = ExecutionOutcome("test", identity, "passed", result)
        self.emit(self._event(identity, "test", "run", state.assessment.lifecycle_status))
        self.workspace.test(identity, output=result)
        return result

    def _finish_check_after_failure(self, error: BaseException) -> None:
        try:
            self.scopes.after_check()
        except BaseException as cleanup_error:
            logger.error("Check cleanup failed: %s", cleanup_error)
            raise BaseExceptionGroup("Check and cleanup failed", [error, cleanup_error]) from None

    def _teardown_scope(self, scope: ResourceScope) -> None:
        self._teardown_matching(lambda node: node.scope == scope)

    def _teardown_outside_suite(self, suite: str) -> None:
        self._teardown_matching(
            lambda node: not self.project.model.contains_suite(node.definition.suite, suite)
        )

    def _teardown_suite(self, suite: str) -> None:
        self._teardown_matching(
            lambda node: self.project.model.contains_suite(suite, node.definition.suite)
        )

    def _teardown_all(self) -> None:
        self._teardown_matching(lambda node: True)

    def _teardown_matching(self, predicate) -> None:
        errors = []
        for identity in reversed(self.started_resources):
            node = self.project.resource(identity)
            if not predicate(node):
                continue
            state = self.resource_states[identity]
            instance = state.instance
            if instance is None:
                continue
            try:
                self.emit(self._event(identity, "resource", "teardown", "started"))
                self.workspace.resource(identity, instance=state.instance)
                instance.teardown()
                self.emit(self._event(identity, "resource", "teardown", "passed"))
            except BaseException as error:
                error.add_note(f"Resource {identity} at {node.definition.source}")
                errors.append(error)
                self.emit(self._event(identity, "resource", "teardown", "failed", error))
                self.workspace.resource(identity, instance=state.instance, error=error)
            finally:
                state.instance = None
                state.started = False
                state.prepared = False
        self.started_resources = [
            identity
            for identity in self.started_resources
            if self.resource_states[identity].started
        ]
        if errors:
            raise BaseExceptionGroup("Resource teardown failed", errors)

    def teardown(self) -> None:
        """Close all started resources; retained state remains available for reports."""
        self.scopes.finish()

    def close_suite(self, suite: str) -> None:
        """Close Suite-scoped resources as a pytest suite collector completes."""
        logger.log(TRACE_LEVEL, "Closing suite %s", suite)
        self.scopes.close_suite(suite)

    def capture_resource_logs(self) -> None:
        """Persist logs from every currently started resource after a check failure."""
        for identity in self.started_resources:
            state = self.resource_states[identity]
            self.workspace.capture_logs("resource", identity, state.instance, report=True)

    def run(self):
        """Run the selected checks through the shared session lifecycle."""
        results = []
        unexpected_outcomes = []
        logger.info("Starting %d checks", len(self.project.test_order))
        try:
            for identity in self.project.test_order:
                node = self.project.test(identity)
                self.scopes.enter_suite(node.definition.suite)
                try:
                    result = self.run_check(identity)
                except BaseException:
                    assessment = self.check_state(identity).assessment
                    if assessment is None or not assessment.matched:
                        raise
                    logger.info("Expected failure for check %s", identity)
                    results.append(None)
                    continue
                results.append(result)
                assessment = self.check_state(identity).assessment
                if assessment is not None and not assessment.matched:
                    error = UnexpectedOutcome(
                        f"Unexpected pass for check '{identity}'; expected outcome 'failed'"
                    )
                    error.add_note(f"Check {identity} at {node.definition.source}")
                    unexpected_outcomes.append(error)
                    logger.error("%s", error)
        except BaseException as error:
            try:
                self.scopes.finish()
            except BaseException as cleanup_error:
                raise BaseExceptionGroup(
                    "Execution and cleanup failed", [error, cleanup_error]
                ) from None
            raise
        self.scopes.finish()
        if unexpected_outcomes:
            raise BaseExceptionGroup("Unexpected check outcomes", unexpected_outcomes)
        logger.info("Completed %d checks", len(results))
        return results
