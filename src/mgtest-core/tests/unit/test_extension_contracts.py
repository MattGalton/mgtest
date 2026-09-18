"""Contract checks applied to built-ins and installed extension definitions."""

from mgtest.api import assert_definition_contract
from mgtest.engine.plugin import PluginImporter


def test_all_registered_definitions_satisfy_the_public_contract():
    importer = PluginImporter()
    importer.load()
    for registry in (importer.catalog.resources, importer.catalog.tests):
        for definition_class in registry.values():
            assert_definition_contract(definition_class)
