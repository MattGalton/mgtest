from mgtest.engine import Engine
from mgtest.engine.plugin import PluginImporter
from mgtest.project.loading import load_project


def test_yaml_specialisations_supply_defaults_and_allow_definition_overrides(tmp_path):
    plugins = tmp_path / "builtin" / "tests"
    plugins.mkdir(parents=True)
    (plugins / "Echo.yml").write_text(
        "specialises: Command\npython_command: \"print('default')\"\nstdout_contains: default\n"
    )
    (plugins / "LoudEcho.yml").write_text("specialises: Echo\nstdout_contains: overridden\n")
    (tmp_path / "t_echo.yaml").write_text(
        "type: LoudEcho\nname: echo\n"
    )

    importer = PluginImporter(extra_paths=[plugins])
    importer.load()
    compiled = Engine(importer.catalog).compile(load_project(tmp_path))

    assert {"Echo", "LoudEcho"} <= set(importer.catalog.tests.keys())
    assert compiled.definitions[".::tests.echo"].spec.python_command == "print('default')"
    assert compiled.definitions[".::tests.echo"].spec.stdout_contains == "overridden"


def test_yaml_resource_specialisation_retains_required_parent_fields(tmp_path):
    plugins = tmp_path / "builtin" / "resources"
    plugins.mkdir(parents=True)
    (plugins / "ShortLived.yml").write_text("specialises: Executable\nargs: [--version]\n")
    (tmp_path / "r_python.yaml").write_text(
        "type: ShortLived\nname: python\npath: python3\n"
    )
    (tmp_path / "t_check.yaml").write_text("type: Command\nname: check\nshell_command: 'true'\n")

    importer = PluginImporter(extra_paths=[plugins])
    importer.load()
    compiled = Engine(importer.catalog).compile(load_project(tmp_path))

    assert compiled.definitions[".::resources.python"].spec.args == ["--version"]
