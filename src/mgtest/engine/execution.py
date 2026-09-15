from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from mgtest.engine.api.resource.spec import ResourceSpec
from mgtest.engine.api.test.spec import TestSpec
from mgtest.engine.configuration import ConfigurationProvider, RunRequest
from mgtest.engine.plugin.plugin_registries import PluginCatalog


@dataclass(frozen=True)
class ExecutionPlan:
    resources: tuple[ResourceSpec, ...]
    tests: tuple[TestSpec, ...]


class ResourceManager(Mapping[str, Any]):
    def __init__(self, specs: tuple[ResourceSpec, ...]):
        self._specs = {spec.name: spec for spec in specs}
        if len(self._specs) != len(specs):
            raise ValueError("Resource names must be unique")
        self._instances: dict[str, Any] = {}
        self._setup_order: list[str] = []

    def required(self, name: str) -> Any:
        if name not in self._specs:
            raise KeyError(f"Unknown resource '{name}'. Available: {sorted(self._specs)}")
        if name not in self._instances:
            instance = self._specs[name].create_instance()
            instance.setup()
            self._instances[name] = instance
            self._setup_order.append(name)
        return self._instances[name].value()

    def start_automatic(self) -> None:
        for name, spec in self._specs.items():
            if spec.auto_start:
                self.required(name)

    def teardown(self) -> None:
        errors: list[BaseException] = []
        for name in reversed(self._setup_order):
            try:
                self._instances[name].teardown()
            except BaseException as error:
                errors.append(error)
        self._setup_order.clear()
        self._instances.clear()
        if errors:
            raise ExceptionGroup("Resource teardown failed", errors)

    def __getitem__(self, name: str) -> Any:
        return self.required(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self._specs)

    def __len__(self) -> int:
        return len(self._specs)


class Engine:
    def __init__(self, catalog: PluginCatalog):
        self.catalog = catalog

    def plan(self, provider: ConfigurationProvider, request: RunRequest) -> ExecutionPlan:
        raw = provider.compose(request)
        resources = tuple(self._parse(item, self.catalog.resources) for item in raw.resources)
        tests = tuple(self._parse(item, self.catalog.tests) for item in raw.tests)
        self._ensure_unique_names(resources, "resource")
        self._ensure_unique_names(tests, "test")
        return ExecutionPlan(resources, tests)

    def run(self, plan: ExecutionPlan) -> list[Any]:
        resources = ResourceManager(plan.resources)
        results: list[Any] = []
        try:
            resources.start_automatic()
            for spec in plan.tests:
                instance = spec.create_instance()
                instance.run(resources)
                results.append(instance.outputs)
            return results
        finally:
            resources.teardown()

    @staticmethod
    def _parse(data, registry):
        type_name = data.get("type")
        if not isinstance(type_name, str):
            raise ValueError("Every definition requires a string 'type'")
        return registry[type_name].model_validate(data)

    @staticmethod
    def _ensure_unique_names(specs, kind: str) -> None:
        names = [spec.name for spec in specs]
        if len(names) != len(set(names)):
            raise ValueError(f"All {kind} names must be unique")
