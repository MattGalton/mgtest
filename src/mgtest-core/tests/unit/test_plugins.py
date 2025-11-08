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
        "from mgtest.api.test import TestSpec\n"
        "class Custom(TestSpec):\n"
        "    type: Literal['Custom']\n"
        "    def create_instance(self): raise NotImplementedError\n"
    )
    importer = PluginImporter(extra_paths=[tmp_path])
    importer.load()
    assert "Custom" in importer.catalog.tests


def test_builtin_registration_count_matches_catalog():
    from mgtest.engine.builtin.registration import register_builtins
    from mgtest.engine.plugin.plugin_registries import PluginCatalog

    catalog = PluginCatalog()
    count = register_builtins(catalog)
    assert "Executable" in catalog.resources
    assert "GitRepository" in catalog.resources
    assert "Command" in catalog.tests
    assert "FileExists" in catalog.tests
    assert "FileMatches" in catalog.tests
    assert "FileBaseline" in catalog.tests
    assert "JsonBaseline" in catalog.tests
    assert "DirectoryBaseline" in catalog.tests
    assert "HttpRequest" in catalog.tests
    assert "StreamRegex" in catalog.tests
    assert "TcpConnect" in catalog.tests
    assert count == len(catalog.resources.keys()) + len(catalog.tests.keys())


def test_entry_points_register_external_resource_and_test_definitions(monkeypatch):
    from mgtest.api.resource import ResourceSpec
    from mgtest.api.test import TestSpec
    from mgtest.engine.plugin import plugin_importer

    class ExternalResource(ResourceSpec):
        TYPE = "ExternalResource"

        def create_instance(self):
            raise NotImplementedError

    class ExternalTest(TestSpec):
        TYPE = "ExternalTest"

        def create_instance(self):
            raise NotImplementedError

    class EntryPoint:
        def __init__(self, plugin_class):
            self.plugin_class = plugin_class

        def load(self):
            return self.plugin_class

    def entry_points(*, group):
        return {
            "mgtest.resources": [EntryPoint(ExternalResource)],
            "mgtest.tests": [EntryPoint(ExternalTest)],
        }[group]

    monkeypatch.setattr(plugin_importer.importlib.metadata, "entry_points", entry_points)
    catalog = PluginImporter()
    catalog.load()

    assert "ExternalResource" in catalog.catalog.resources
    assert "ExternalTest" in catalog.catalog.tests


def test_type_defaults_to_the_class_name_and_output_is_optional():
    from mgtest.api.test import TestSpec

    class Simple(TestSpec):
        def create_instance(self):
            raise NotImplementedError

    class StableName(Simple):
        TYPE = "stable-name"

    assert Simple.type_name() == "Simple"
    assert Simple.output_model() is None
    assert StableName.type_name() == "stable-name"


def test_new_nested_builtin_is_discovered_without_registration_changes(tmp_path, monkeypatch):
    import sys

    from mgtest.engine.builtin import resources
    from mgtest.engine.builtin.registration import register_builtins
    from mgtest.engine.plugin.plugin_registries import PluginCatalog

    baseline = register_builtins(PluginCatalog())
    package = tmp_path / "discovery_probe"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "spec.py").write_text(
        "from abc import abstractmethod\n"
        "from mgtest.api.resource import ResourceSpec\n"
        "class AbstractProbe(ResourceSpec):\n"
        "    @abstractmethod\n"
        "    def create_instance(self): ...\n"
        "class DiscoveredProbe(AbstractProbe):\n"
        "    def create_instance(self): raise NotImplementedError\n"
        "Alias = DiscoveredProbe\n"
    )
    monkeypatch.setattr(resources, "__path__", [*resources.__path__, str(tmp_path)])
    try:
        catalog = PluginCatalog()
        assert register_builtins(catalog) == baseline + 1
        assert "DiscoveredProbe" in catalog.resources
        assert "__CHANGE_ME__" not in catalog.resources
        importer = PluginImporter()
        count = importer.load()
        assert count == len(importer.catalog.resources.keys()) + len(importer.catalog.tests.keys())
    finally:
        prefix = resources.__name__ + ".discovery_probe"
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]


def test_registration_hook_counts_specs_instead_of_callbacks(tmp_path, monkeypatch):
    from mgtest.engine.plugin import plugin_importer

    monkeypatch.delenv("MGT_PLUGIN_PATHS", raising=False)
    monkeypatch.setattr(plugin_importer.importlib.metadata, "entry_points", lambda **kwargs: [])
    baseline = PluginImporter().load()
    (tmp_path / "hook.py").write_text(
        "from mgtest.api.test import TestSpec\n"
        "class First(TestSpec):\n"
        "    def create_instance(self): raise NotImplementedError\n"
        "class Second(First):\n"
        "    pass\n"
        "def register(catalog):\n"
        "    catalog.tests.register(First.type_name(), First)\n"
        "    catalog.tests.register(Second.type_name(), Second)\n"
    )
    importer = PluginImporter(extra_paths=[tmp_path])
    assert importer.load() == baseline + 2
