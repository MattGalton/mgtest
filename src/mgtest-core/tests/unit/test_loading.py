from mgtest.engine import Engine
from mgtest.engine.plugin import PluginImporter
from mgtest.project.loading import load_project
from mgtest.project.selection import select


def test_project_variables_resolve_environment_and_other_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("MGTEST_LOADING_HOST", "example.test")
    (tmp_path / "vars.yaml").write_text(
        "host: '${oc.env:MGTEST_LOADING_HOST,localhost}'\n"
        "url: 'https://${vars.host}/health'\n"
    )
    (tmp_path / "t_check.yaml").write_text(
        "type: FileExists\nname: check\npath: '${vars.url}'\n"
    )

    assert load_project(tmp_path).suites["."].variables == {
        "host": "example.test",
        "url": "https://example.test/health",
    }


def test_project_variable_resolution_preserves_execution_references(tmp_path):
    (tmp_path / "vars.yaml").write_text(
        "endpoint: 'prefix-${resources.service.outputs.url}'\n"
        "result: '${mgtest:tests.check.outputs.result}'\n"
    )
    (tmp_path / "t_check.yaml").write_text(
        "type: FileExists\nname: check\npath: '${vars.endpoint}'\n"
    )

    assert load_project(tmp_path).suites["."].variables == {
        "endpoint": "prefix-${resources.service.outputs.url}",
        "result": "${mgtest:tests.check.outputs.result}",
    }


def test_loader_requires_s_prefix_for_directories_and_groups_existing_checks(tmp_path):
    for name in ("first", "second"):
        (tmp_path / f"t_{name}.yaml").write_text(
            f"type: FileExists\nname: {name}\npath: .\n"
        )
    ignored = tmp_path / "ordinary"
    ignored.mkdir()
    (ignored / "t_ignored.yaml").write_text("type: FileExists\nname: ignored\npath: .\n")
    (tmp_path / "s_release.yaml").write_text("tests: [first, second, first]\n")

    project = load_project(tmp_path)

    assert set(project.definitions) == {".::tests.first", ".::tests.second"}
    assert project.suites["s_release"].test_members == (
        ".::tests.first",
        ".::tests.second",
    )
    assert project.tests_in_selection("s_release") == {
        ".::tests.first",
        ".::tests.second",
    }

    select(project, "s_release")
    importer = PluginImporter()
    importer.load()
    compiled = Engine(importer.catalog).compile(project)
    assert tuple(compiled.definitions) == (".::tests.first", ".::tests.second")
    assert compiled.test_order == (".::tests.first", ".::tests.second")
