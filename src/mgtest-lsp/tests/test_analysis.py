import json
from pathlib import Path

from mgtest.tooling.analysis import AnalysisService, is_mgtest_path, main
from mgtest.tooling.analysis.items import AnalysisItems
from mgtest_lsp.plugin import pylsp_settings
from pydantic import BaseModel, Field


def test_recognises_mgtest_document_names():
    assert is_mgtest_path(Path("r_service.yaml"))
    assert is_mgtest_path(Path("t_check.yml"))
    assert is_mgtest_path(Path("vars.yaml"))
    assert not is_mgtest_path(Path("notes.yaml"))


def test_recognises_and_analyses_yaml_specialisations(tmp_path):
    project = tmp_path / "mgtest"
    plugins = project / "builtin" / "tests"
    plugins.mkdir(parents=True)
    echo = plugins / "Echo.yml"
    echo.write_text("specialises: Command\npython_command: \"print('hello')\"\n")

    service = AnalysisService(project)

    assert is_mgtest_path(echo)
    assert service.analyse(echo, echo.read_text()) == []
    assert any(
        item["label"] == "Command" for item in service.completions(echo, "specialises: ", 0, 13)
    )
    field_labels = {
        item["label"] for item in service.completions(echo, echo.read_text() + "\n", 2, 0)
    }
    assert "name" in field_labels
    assert "python_command" not in field_labels
    assert service.definitions(project / "t_echo.yaml", "type: Echo\n", 0, 7) == [echo]


def test_reports_invalid_yaml_specialisation(tmp_path):
    path = tmp_path / "builtin" / "resources" / "Broken.yml"
    path.parent.mkdir(parents=True)
    path.write_text("specialises: Missing\n")

    diagnostics = AnalysisService(tmp_path).analyse(path, path.read_text())

    assert diagnostics[0].message == "Unknown resource type 'Missing'"


def test_reports_unknown_type():
    diagnostics = AnalysisService().analyse(
        Path("t_unknown.yaml"), "tests:\n  - name: check\n    type: Missing\n"
    )
    assert diagnostics[0].message == "Unknown test type 'Missing'"


def test_completes_installed_definition_types():
    completions = AnalysisService().completions(Path("t_check.yaml"), "type: ", 0, 6)
    file_exists = next(item for item in completions if item["label"] == "FileExists")
    assert file_exists["detail"].startswith("mgtest test type")
    assert "exists" in file_exists["documentation"]["value"]
    assert "name: ${1}" in file_exists["insertText"]
    assert "path: ${2}" in file_exists["insertText"]


def test_completes_type_key_for_an_empty_definition_document():
    completions = AnalysisService().completions(Path("r_archive.yaml"), "# a resource\n", 1, 0)

    assert completions[0]["label"] == "type"
    assert completions[0]["insertText"] == "type: "


def test_completes_resource_types_for_resource_documents():
    completions = AnalysisService().completions(Path("r_workspace.yaml"), "type: ", 0, 6)

    temporary_directory = next(
        item for item in completions if item["label"] == "TemporaryDirectory"
    )
    assert temporary_directory["detail"].startswith("mgtest resource type")
    assert "temporary directory" in temporary_directory["documentation"]["value"]


def test_completes_visible_dag_references_for_a_field_value(tmp_path):
    project = tmp_path / "mgtest"
    (project / "builtin").mkdir(parents=True)
    suite = project / "s_example"
    suite.mkdir()
    (project / "vars.yaml").write_text("message: hello\n")
    (suite / "r_workspace.yaml").write_text("type: TemporaryDirectory\nname: workspace\n")
    check = suite / "t_check.yaml"
    source = 'type: FileExists\nname: check\npath: "${mgtest:resources.workspace.outputs.path}"\n'
    check.write_text(source)
    another_check = suite / "t_another_check.yaml"
    another_check.write_text(
        "type: FileExists\nname: another-check\n"
        'path: "${mgtest:resources.workspace.outputs.path}"\n'
    )
    service = AnalysisService(project)

    resource_names = service.completions(
        check, "type: FileExists\nname: check\npath: ${mgtest:resources.w", 2, 27
    )
    assert {item["label"] for item in resource_names} == {"workspace"}

    outputs = service.completions(
        check,
        "type: FileExists\nname: check\npath: ${mgtest:resources.workspace.outputs.p",
        2,
        45,
    )
    assert {item["label"] for item in outputs} == {"path"}

    value_references = service.completions(check, "type: FileExists\nname: check\npath: ", 2, 6)
    assert {
        "${vars.message}",
        "${mgtest:resources.workspace.outputs.path}",
    } <= {item["label"] for item in value_references}
    variable = next(item for item in value_references if item["label"] == "${vars.message}")
    output = next(
        item
        for item in value_references
        if item["label"] == "${mgtest:resources.workspace.outputs.path}"
    )
    assert "mgtest variable `message`" in variable["documentation"]["value"]
    assert "TemporaryDirectory" in output["documentation"]["value"]

    hover = service.hover(check, source, 2, source.splitlines()[2].index("workspace"))
    assert hover is not None
    assert "TemporaryDirectory" in hover

    assert service.definitions(check, "path: ${vars.message}", 0, 14) == [project / "vars.yaml"]
    assert service.definitions(
        check, "path: ${mgtest:resources.workspace.outputs.path}", 0, 31
    ) == [suite / "r_workspace.yaml"]

    usages = service.references(check, source, 2, source.splitlines()[2].index("workspace"))
    assert usages == [
        {
            "uri": check.as_uri(),
            "range": {
                "start": {"line": 2, "character": source.splitlines()[2].index("${")},
                "end": {
                    "line": 2,
                    "character": source.splitlines()[2].index("}") + 1,
                },
            },
        },
        {
            "uri": another_check.as_uri(),
            "range": {
                "start": {"line": 2, "character": 7},
                "end": {"line": 2, "character": 49},
            },
        },
    ]

    quoted_variable = service.completions(
        check, 'type: FileExists\nname: check\npath: "${vars.m', 2, 34
    )
    assert {item["label"] for item in quoted_variable} == {"message"}

    resolver = AnalysisService().completions(Path("r_archive.yaml"), "message: ${oc.e", 0, 16)
    assert {item["label"] for item in resolver} == {"oc.env"}

    dependencies = service.completions(check, "type: FileExists\nname: check\ndepends_on: ", 2, 12)
    assert "resources.workspace" in {item["label"] for item in dependencies}


def test_completes_fields_from_a_type():
    completions = AnalysisService().completions(
        Path("t_check.yaml"), "tests:\n  - type: FileExists\n    ", 2, 4
    )
    assert {"name", "path"} <= {item["label"] for item in completions}
    path = next(item for item in completions if item["label"] == "path")
    assert path["insertText"] == "path: "
    expected_outcome = next(item for item in completions if item["label"] == "expected_outcome")
    assert expected_outcome["insertText"] == 'expected_outcome: "passed"'


def test_completes_a_partially_typed_field_key():
    completions = AnalysisService().completions(
        Path("t_archive.yaml"), "type: ArchiveContains\nname: archive\nexp", 2, 3
    )

    assert "expected_outcome" in {item["label"] for item in completions}


def test_does_not_complete_definition_fields_inside_yaml_collections():
    service = AnalysisService()

    list_completions = service.completions(
        Path("t_archive.yaml"),
        "type: ArchiveContains\nname: archive\ncontains:\n  - exp",
        3,
        7,
    )
    mapping_completions = service.completions(
        Path("t_request.yaml"),
        "type: HttpRequest\nname: request\nheaders:\n  exp",
        3,
        5,
    )

    assert list_completions == []
    assert mapping_completions == []


def test_hover_includes_field_defaults_literals_and_constraints():
    service = AnalysisService()
    source = (
        "type: ArchiveContains\nname: archive\npath: archive.zip\ncontains: [message.txt]\n"
        "expected_outcome: passed\ntimeout: 1\n"
    )

    expected_outcome = service.hover(
        Path("t_archive.yaml"), source, 4, source.splitlines()[4].index("expected_outcome")
    )
    timeout = service.hover(
        Path("t_archive.yaml"), source, 5, source.splitlines()[5].index("timeout")
    )

    assert expected_outcome is not None
    assert '**Default:** `"passed"`' in expected_outcome
    assert '**Accepted values:** `"passed"`, `"failed"`' in expected_outcome
    assert timeout is not None
    assert "**Default:** `null`" in timeout
    assert "**Constraints:** greater than `0`" in timeout


def test_field_documentation_includes_declared_examples():
    class ExampleSpec(BaseModel):
        value: str = Field(examples=["example-value"])

    documentation = AnalysisItems.field_documentation("value", ExampleSpec.model_fields["value"])

    assert '**Examples:** `"example-value"`' in documentation


def test_does_not_complete_keys_already_in_the_document():
    completions = AnalysisService().completions(
        Path("t_check.yaml"), "type: FileExists\nname: check\npa", 2, 2
    )

    assert "type" not in {item["label"] for item in completions}
    assert "name" not in {item["label"] for item in completions}


def test_offers_quick_fixes_for_unknown_types_and_missing_required_fields():
    service = AnalysisService()
    unknown_type = "type: Missing\nname: check\npath: result.txt\n"

    type_fixes = service.code_actions(
        Path("t_check.yaml"),
        unknown_type,
        {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 13}},
    )
    assert any(action["title"] == "Replace with FileExists" for action in type_fixes)

    missing_field = "type: FileExists\nname: check\n"
    field_fixes = service.code_actions(
        Path("t_check.yaml"),
        missing_field,
        {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 0}},
    )
    path_fix = next(
        action for action in field_fixes if action["title"] == "Add required field 'path'"
    )
    assert next(iter(path_fix["edit"]["changes"].values()))[0]["newText"] == "\npath: "


def test_offers_a_dependency_quick_fix_for_output_references(tmp_path):
    project = tmp_path / "mgtest"
    (project / "builtin").mkdir(parents=True)
    resource = project / "r_workspace.yaml"
    resource.write_text("type: TemporaryDirectory\nname: workspace\n")
    check = project / "t_check.yaml"
    source = "type: FileExists\nname: check\npath: ${resources.workspace.outputs.path}\n"

    actions = AnalysisService(project).code_actions(
        check,
        source,
        {"start": {"line": 2, "character": 6}, "end": {"line": 2, "character": 45}},
    )

    dependency = next(
        action for action in actions if action["title"] == "Add dependency 'resources.workspace'"
    )
    assert next(iter(dependency["edit"]["changes"].values()))[0]["newText"] == (
        "\ndepends_on:\n  - resources.workspace\n"
    )


def test_reports_unknown_reference_when_the_project_is_known(tmp_path):
    path = tmp_path / "t_check.yaml"
    source = (
        "tests:\n  - name: check\n    type: FileExists\n"
        "    path: '${resources.nope.outputs.path}'\n"
    )
    diagnostics = AnalysisService(tmp_path).analyse(path, source)
    assert diagnostics[-1].message == "Unknown or invisible resources.nope"
    assert (diagnostics[-1].line, diagnostics[-1].character) == (3, 11)


def test_reports_unknown_output_at_the_reference(tmp_path):
    project = tmp_path / "mgtest"
    (project / "builtin").mkdir(parents=True)
    suite = project / "s_example"
    suite.mkdir()
    (suite / "r_workspace.yaml").write_text("type: TemporaryDirectory\nname: workspace\n")
    check = suite / "t_check.yaml"
    source = "type: FileExists\nname: check\npath: '${resources.workspace.outputs.missing}'\n"
    check.write_text(source)

    diagnostics = AnalysisService(project).analyse(check, source)

    assert diagnostics[-1].message == "Unknown output 'missing' on resources.workspace"
    assert (diagnostics[-1].line, diagnostics[-1].character) == (2, 7)


def test_reports_dependency_cycles_at_the_closing_dependency(tmp_path):
    project = tmp_path / "mgtest"
    (project / "builtin").mkdir(parents=True)
    first = project / "t_first.yaml"
    second = project / "t_second.yaml"
    first.write_text("type: FileExists\nname: first\npath: first.txt\ndepends_on: [tests.second]\n")
    second.write_text(
        "type: FileExists\nname: second\npath: second.txt\ndepends_on: [tests.first]\n"
    )

    diagnostics = AnalysisService(project).analyse(second, second.read_text())

    assert [diagnostic.message for diagnostic in diagnostics] == [
        "Dependency cycle: .::tests.first -> .::tests.second -> .::tests.first"
    ]
    assert diagnostics[-1].message == (
        "Dependency cycle: .::tests.first -> .::tests.second -> .::tests.first"
    )
    assert diagnostics[-1].code == "cycle"
    assert (diagnostics[-1].line, diagnostics[-1].character) == (3, 0)


def test_returns_document_symbols():
    symbols = AnalysisService().symbols(
        Path("t_check.yaml"),
        "tests:\n  - name: check\n    type: FileExists\n    path: output.txt\n",
    )
    assert symbols[0]["name"] == "check"


def test_disables_python_providers_in_the_dedicated_server():
    plugins = pylsp_settings()["plugins"]
    assert plugins["jedi_completion"]["enabled"] is False
    assert plugins["pyflakes"]["enabled"] is False


def test_analysis_main_reports_diagnostics(tmp_path, capsys):
    path = tmp_path / "t_invalid.yaml"
    path.write_text("type: Unknown\nname: check\n")

    assert main(["--root", str(tmp_path), str(path)]) == 1
    assert "Unknown test type 'Unknown'" in capsys.readouterr().out


def test_analysis_main_writes_json(tmp_path, capsys):
    path = tmp_path / "t_valid.yaml"
    path.write_text("type: FileExists\nname: check\npath: result.txt\n")

    assert main(["--root", str(tmp_path), "--json", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["diagnostics"] == []


def test_main_cli_forwards_to_analysis(tmp_path, capsys):
    from mgtest.cli.mgtest_analyse import run

    path = tmp_path / "t_valid.yaml"
    path.write_text("type: FileExists\nname: check\npath: result.txt\n")
    args = type("Args", (), {"root": tmp_path, "json": False, "paths": [path]})()

    assert run(args) == 0
    assert capsys.readouterr().out == ""


def test_analysis_main_loads_project_local_plugins(tmp_path, capsys):
    project = tmp_path / "mgtest"
    plugins = project / "builtin" / "resources"
    plugins.mkdir(parents=True)
    (plugins / "fixture.py").write_text(
        "from mgtest.api.resource import ResourceSpec\n"
        "from mgtest.api.resource import ResourceInstance\n"
        "class FixtureInstance(ResourceInstance):\n"
        "    def setup(self): pass\n"
        "    def teardown(self): pass\n"
        "class Fixture(ResourceSpec):\n"
        "    def create_instance(self): return FixtureInstance(self)\n"
    )
    path = project / "r_fixture.yaml"
    path.write_text("type: Fixture\nname: fixture\n")

    assert main([str(path)]) == 0
    assert capsys.readouterr().out == ""
