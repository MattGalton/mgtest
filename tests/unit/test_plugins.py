from mgtest.engine.plugin import PluginImporter


def test_engine_catalogs_are_isolated():
    first = PluginImporter()
    second = PluginImporter()
    first.load()
    second.load()
    assert first.catalog is not second.catalog
    assert first.catalog.tests is not second.catalog.tests


def test_development_plugin_uses_unique_module_name(tmp_path):
    (tmp_path / "spec.py").write_text(
        "from typing import Literal\n"
        "from mgtest.engine.api.test.spec import TestSpec\n"
        "class Custom(TestSpec):\n"
        "    TYPE = 'Custom'\n"
        "    type: Literal['Custom']\n"
        "    def create_instance(self): raise NotImplementedError\n"
    )
    importer = PluginImporter(extra_paths=[tmp_path])
    importer.load()
    assert "Custom" in importer.catalog.tests
