from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path

from mgtest.api.resource import ResourceSpec
from mgtest.api.test import TestSpec
from mgtest.engine.builtin.registration import register_builtins
from mgtest.engine.plugin.plugin_registries import PluginCatalog
from mgtest.engine.plugin.yaml_specialization import load_yaml_specialisations

logger = logging.getLogger(__name__)


class PluginImporter:
    """Populate an engine catalog from built-ins, entry points, and dev paths."""

    ENTRY_POINT_GROUPS = {"mgtest.resources": "resources", "mgtest.tests": "tests"}

    def __init__(
        self,
        catalog: PluginCatalog | None = None,
        extra_paths: list[Path] | None = None,
        *,
        ignore_yaml_specialisation_errors: bool = False,
    ):
        self.catalog = catalog or PluginCatalog()
        self.extra_paths = list(extra_paths or ())
        self.ignore_yaml_specialisation_errors = ignore_yaml_specialisation_errors
        env_paths = os.environ.get("MGT_PLUGIN_PATHS")
        if env_paths:
            self.extra_paths.extend(Path(path) for path in env_paths.split(os.pathsep) if path)

    def load(self) -> int:
        count = 0
        count += register_builtins(self.catalog)
        for group, registry_name in self.ENTRY_POINT_GROUPS.items():
            registry = getattr(self.catalog, registry_name)
            for entry_point in importlib.metadata.entry_points(group=group):
                plugin_class = entry_point.load()
                registry.register(plugin_class.type_name(), plugin_class)
                count += 1
        for path in self.extra_paths:
            count += self._load_development_path(path)
        logger.info("Loaded %d plugin definitions", count)
        return count

    def _load_development_path(self, path: Path) -> int:
        if not path.is_dir():
            raise ValueError(f"Plugin path is not a directory: {path}")
        count = 0
        logger.debug("Loading development plugins from %s", path)
        for py_file in sorted(path.rglob("*.py")):
            if py_file.name == "__init__.py":
                continue
            digest = hashlib.sha256(str(py_file.resolve()).encode()).hexdigest()[:12]
            module_name = f"mgtest_external_{py_file.stem}_{digest}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot import plugin {py_file}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            register = getattr(module, "register", None)
            if callable(register):
                before = len(self.catalog.resources.keys()) + len(self.catalog.tests.keys())
                register(self.catalog)
                after = len(self.catalog.resources.keys()) + len(self.catalog.tests.keys())
                count += after - before
                continue
            for _, candidate in inspect.getmembers(module, inspect.isclass):
                if candidate.__module__ != module_name or inspect.isabstract(candidate):
                    continue
                if issubclass(candidate, ResourceSpec):
                    self.catalog.resources.register(candidate.type_name(), candidate)
                    count += 1
                elif issubclass(candidate, TestSpec):
                    self.catalog.tests.register(candidate.type_name(), candidate)
                    count += 1
        # Generic development paths remain Python-only. YAML type declarations are
        # deliberately scoped to the conventional project plugin directories so a
        # directory containing ordinary plugin files needs no resources/tests shape.
        if path.name in {"resources", "tests"}:
            count += load_yaml_specialisations(
                path, self.catalog, strict=not self.ignore_yaml_specialisation_errors
            )
        return count
