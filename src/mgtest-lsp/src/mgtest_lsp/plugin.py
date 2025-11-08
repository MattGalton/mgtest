"""python-lsp-server hooks for mgtest YAML documents."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from mgtest.tooling.analysis import AnalysisService, is_mgtest_path
from pylsp import hookimpl


def _path(document) -> Path:
    return Path(unquote(urlparse(document.uri).path))


def _service(workspace) -> AnalysisService:
    service = getattr(workspace, "_mgtest_service", None)
    if service is None:
        service = AnalysisService(Path(workspace.root_path))
        workspace._mgtest_service = service
    return service


@hookimpl
def pylsp_settings(**_kwargs):
    """Make the ``mgtest-lsp`` command a YAML-only pylsp instance.

    pylsp's bundled providers assume every open document is Python. Disabling them
    avoids Python syntax diagnostics and Jedi work for mgtest YAML files. A user
    should run their normal Python pylsp separately if they need Python features.
    """
    providers = (
        "autopep8",
        "flake8",
        "jedi_completion",
        "jedi_definition",
        "jedi_hover",
        "jedi_references",
        "jedi_signature_help",
        "jedi_symbols",
        "jedi_type_definition",
        "mccabe",
        "pycodestyle",
        "pydocstyle",
        "pyflakes",
        "pylint",
        "rope_autoimport",
        "rope_completion",
        "yapf",
    )
    return {"plugins": {provider: {"enabled": False} for provider in providers}}


@hookimpl
def pylsp_lint(workspace, document, **_kwargs):
    path = _path(document)
    if not is_mgtest_path(path):
        return []
    return [
        {
            "source": "mgtest",
            "code": issue.code,
            "message": issue.message,
            "severity": issue.severity,
            "range": {
                "start": {"line": issue.line, "character": issue.character},
                "end": {"line": issue.end_line, "character": issue.end_character},
            },
        }
        for issue in _service(workspace).analyse(path, document.source)
    ]


@hookimpl
def pylsp_completions(workspace, document, position, **_kwargs):
    return _service(workspace).completions(
        _path(document), document.source, position["line"], position["character"]
    )


@hookimpl
def pylsp_hover(workspace, document, position, **_kwargs):
    contents = _service(workspace).hover(
        _path(document), document.source, position["line"], position["character"]
    )
    return {"contents": {"kind": "markdown", "value": contents}} if contents else None


@hookimpl
def pylsp_definitions(workspace, document, position, **_kwargs):
    return [
        {
            "uri": target.as_uri(),
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 1},
            },
        }
        for target in _service(workspace).definitions(
            _path(document), document.source, position["line"], position["character"]
        )
    ]


@hookimpl
def pylsp_references(workspace, document, position, **_kwargs):
    return _service(workspace).references(
        _path(document), document.source, position["line"], position["character"]
    )


@hookimpl
def pylsp_document_symbols(workspace, document, **_kwargs):
    return _service(workspace).symbols(_path(document), document.source)


@hookimpl
def pylsp_code_actions(workspace, document, range, **_kwargs):
    return _service(workspace).code_actions(_path(document), document.source, range)


@hookimpl
def pylsp_workspace_configuration_changed(workspace, **_kwargs):
    if hasattr(workspace, "_mgtest_service"):
        del workspace._mgtest_service
