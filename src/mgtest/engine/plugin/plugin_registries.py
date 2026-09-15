from dataclasses import dataclass, field

from mgtest.engine.plugin.plugin_registry import PluginRegistry


@dataclass
class PluginCatalog:
    """Registries owned by one engine, avoiding process-global plugin state."""

    resources: PluginRegistry = field(default_factory=PluginRegistry)
    tests: PluginRegistry = field(default_factory=PluginRegistry)


# Compatibility catalog for schema tooling callers that do not supply an engine.
DEFAULT_CATALOG = PluginCatalog()
RESOURCE_REGISTRY = DEFAULT_CATALOG.resources
TEST_REGISTRY = DEFAULT_CATALOG.tests
