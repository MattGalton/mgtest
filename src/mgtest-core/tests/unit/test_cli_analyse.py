from mgtest.cli.mgtest_analyse import run
from mgtest.tooling.analysis import main


def test_main_cli_uses_core_analysis_without_the_lsp_package(tmp_path, capsys):
    path = tmp_path / "t_valid.yaml"
    path.write_text("type: FileExists\nname: check\npath: result.txt\n")
    args = type("Args", (), {"root": tmp_path, "json": False, "paths": [path]})()

    assert run(args) == 0
    assert capsys.readouterr().out == ""


def test_core_analysis_cli_validates_project_yaml_specialisations(tmp_path, capsys):
    project = tmp_path / "mgtest"
    specialisation = project / "builtin" / "tests" / "Echo.yml"
    specialisation.parent.mkdir(parents=True)
    specialisation.write_text("specialises: Command\npython_command: \"print('hello')\"\n")

    assert main(["--root", str(project), str(specialisation)]) == 0
    assert capsys.readouterr().out == ""
