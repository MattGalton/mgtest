from dataclasses import dataclass, field

from mgtest.engine.plugin.plugin_registry import PluginRegistry


@dataclass
class PluginCatalog:
    """Registries owned by one engine, avoiding process-global plugin state."""

    resources: PluginRegistry = field(default_factory=PluginRegistry)
    tests: PluginRegistry = field(default_factory=PluginRegistry)
