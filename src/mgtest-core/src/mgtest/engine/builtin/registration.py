import importlib
import inspect
import logging
import pkgutil
from types import ModuleType

from mgtest.api.resource import ResourceSpec
from mgtest.api.test import TestSpec
from mgtest.engine.builtin import resources, tests
from mgtest.engine.plugin.plugin_registries import PluginCatalog

logger = logging.getLogger(__name__)


def _discover_specs(package: ModuleType, base: type):
    """Find concrete specs defined in a package, excluding imports and aliases."""
    module_names = [package.__name__]
    module_names.extend(
        module.name for module in pkgutil.walk_packages(package.__path__, package.__name__ + ".")
    )
    seen = set()
    for module_name in sorted(module_names):
        module = importlib.import_module(module_name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if (
                candidate.__module__ == module_name
                and issubclass(candidate, base)
                and not inspect.isabstract(candidate)
                and candidate not in seen
            ):
                seen.add(candidate)
                yield candidate


def register_builtins(catalog: PluginCatalog) -> int:
    """Discover built-in resource/test specs and return the number registered."""
    count = 0
    for package, base, registry in (
        (resources, ResourceSpec, catalog.resources),
        (tests, TestSpec, catalog.tests),
    ):
        for spec in _discover_specs(package, base):
            registry.register(spec.type_name(), spec)
            count += 1
    logger.debug("Registered %d built-in definitions", count)
    return count
