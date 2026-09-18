"""Per-run artifact workspaces."""

from __future__ import annotations

import contextlib
import json
import logging
import traceback
import uuid
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mgtest.runtime.cache import CacheStore
from mgtest.runtime.context import active_workspace
from mgtest.runtime.state import load_settings, now, runtime_path

logger = logging.getLogger(__name__)


class NullWorkspace:
    """Workspace contract implementation used when callers do not retain artifacts."""

    @contextlib.contextmanager
    def active(self):
        """Provide the same context-manager contract as a persisted workspace."""
        yield self

    def resource(self, identity: str, instance=None, error=None) -> None:
        """Discard one resource lifecycle record."""

    def test(self, identity: str, output=None, error=None, instance=None) -> None:
        """Discard one test lifecycle record."""

    def capture_logs(self, kind: str, identity: str, instance, *, report: bool = False) -> None:
        """Discard optional instance diagnostics."""


class RunWorkspace:
    """One run's manifest, logs, rendered plan, and shared local cache."""

    category = "runs"

    def __init__(self, root: Path, run_id: str, cache: CacheStore):
        self.root = root
        self.run_id = run_id
        self.path = runtime_path(root) / self.category / run_id
        self.path.mkdir(parents=True, exist_ok=False)
        self.cache = cache
        self.manifest = {
            "run_id": run_id,
            "started_at": now(),
            "status": "running",
            "resources": {},
            "tests": {},
        }

    @classmethod
    def create(cls, root: Path, compiled) -> RunWorkspace:
        root = root.resolve()
        settings = load_settings(root)
        state = runtime_path(root)
        cache = CacheStore(state / "cache", settings["cache"]["max_size_mb"])
        cache.root.mkdir(parents=True, exist_ok=True)
        cache.prune()
        from mgtest.runtime.maintenance import prune_runtime

        prune_runtime(root)
        run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        workspace = cls(root, run_id, cache)
        workspace._write_yaml("resolved-config.yaml", _resolved_config(compiled))
        workspace._flush()
        logger.debug("Created run workspace %s", workspace.path)
        return workspace

    @contextlib.contextmanager
    def active(self):
        """Make this workspace available while a resource runs."""
        with active_workspace(self):
            yield self

    def resource(
        self,
        identity: str,
        instance: Any | None = None,
        error: BaseException | None = None,
    ):
        entry = self.manifest["resources"].setdefault(identity, {})
        entry["status"] = "failed" if error else "ready"
        if error:
            self._write_error(Path("resources") / _name(identity) / "failure.txt", error)
        if instance is not None:
            self.capture_logs("resource", identity, instance, report=error is not None)
        self._flush()

    def test(
        self,
        identity: str,
        output: Any | None = None,
        error: BaseException | None = None,
        instance: Any | None = None,
    ):
        entry = self.manifest["tests"].setdefault(identity, {})
        entry["status"] = "failed" if error else "passed"
        if error:
            self.manifest["status"] = "failed"
            self._write_error(Path("tests") / _name(identity) / "failure.txt", error)
            if instance is not None:
                self.capture_logs("test", identity, instance, report=True)
        elif output is not None:
            self._write_json(Path("tests") / _name(identity) / "outputs.json", _plain(output))
        self._flush()

    def capture_logs(self, kind: str, identity: str, instance: Any, *, report: bool = False):
        """Save optional instance logs and report them when a check or resource fails."""
        relative = Path(f"{kind}s") / _name(identity)
        logs = getattr(instance, "logs", None)
        if not callable(logs):
            return
        try:
            content = str(logs())
        except Exception as error:
            logger.warning("Could not collect logs for %s %s", kind, identity, exc_info=error)
            self._write_error(relative / "logs-error.txt", error)
            return
        self._write_text(relative / "logs.txt", content)
        if report and content:
            logger.error("Captured logs for failed %s %s:\n%s", kind, identity, content)

    def finalize(self, error: BaseException | None = None):
        if error:
            self.manifest["status"] = "failed"
            self._write_error(Path("failure.txt"), error)
        elif self.manifest["status"] == "running":
            self.manifest["status"] = "passed"
        self.manifest["finished_at"] = now()
        self._flush()
        logger.debug(
            "Finalized run workspace %s with status %s", self.path, self.manifest["status"]
        )

    def _write_error(self, relative: Path, error: BaseException):
        self._write_text(relative, "".join(traceback.format_exception(error)))

    def _write_yaml(self, relative: str | Path, value: Any):
        self._write_text(relative, yaml.safe_dump(value, sort_keys=False))

    def _write_json(self, relative: Path, value: Any):
        self._write_text(relative, json.dumps(value, indent=2, default=str) + "\n")

    def _write_text(self, relative: str | Path, content: str):
        path = self.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def _flush(self):
        self._write_json(Path("manifest.json"), self.manifest)


class GetWorkspace(RunWorkspace):
    """Persist resources collected for one local inspection environment."""

    category = "gets"

    def describe_get(
        self, target: str, resources: tuple[str, ...], prerequisite_tests: tuple[str, ...]
    ) -> None:
        self.manifest["get"] = {
            "target": target,
            "resources": list(resources),
            "prerequisite_tests": list(prerequisite_tests),
        }
        self._flush()

    def record_environment(self, environment: dict[str, str]) -> None:
        """Save mgtest-provided environment variables without copying host secrets."""
        values = {key: value for key, value in environment.items() if key.startswith("MGTEST_")}
        self.manifest.setdefault("get", {})["environment"] = values
        self._write_json(Path("environment.json"), values)
        self._flush()


def _resolved_config(compiled) -> dict:
    resources = getattr(compiled, "resources", {})
    tests = getattr(compiled, "tests", {})
    return {
        "resources": {
            identity: _plain(node.data)
            for identity, node in resources.items()
        },
        "tests": {
            identity: _plain(node.data)
            for identity, node in tests.items()
        },
        "test_order": list(compiled.test_order),
    }


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, type(None) | str | int | float | bool):
        return value
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    return str(value)


def _name(identity: str) -> str:
    return identity.replace("/", "_").replace(":", "_")
