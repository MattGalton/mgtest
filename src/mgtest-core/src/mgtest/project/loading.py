"""Recursive YAML discovery for an mgtest project."""

import logging
import re
from pathlib import Path

import yaml
from omegaconf import OmegaConf

from mgtest.engine.project.model import ProjectError, ProjectModel, SourceLocation, Suite
from mgtest.project.layout import ProjectLayout
from mgtest.project.selectors import split_check_selector

logger = logging.getLogger(__name__)
_PROTECTED_EXPRESSION = re.compile(r"\$\{(?:mgtest:)?(?:resources|tests)\.[^{}]+\}")


def load_project(root: Path) -> ProjectModel:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory does not exist: {root}")
    model = ProjectModel(root, {}, {})
    layout = ProjectLayout(root)
    directories = [
        root,
        *sorted(path for path in root.rglob("*") if layout.is_discoverable_directory(path)),
    ]
    for directory in directories:
        identifier = "." if directory == root else directory.relative_to(root).as_posix()
        parent = (
            None if identifier == "." else (directory.parent.relative_to(root).as_posix() or ".")
        )
        model.suites[identifier] = Suite(identifier, directory, parent)
        if parent is not None:
            model.suites[parent].children.append(identifier)
    for suite in model.suites.values():
        inherited = dict(model.suites[suite.parent].variables) if suite.parent else {}
        vars_path = next(
            (
                suite.path / name
                for name in ("vars.yaml", "vars.yml")
                if (suite.path / name).is_file() and layout.is_variables_document(suite.path / name)
            ),
            None,
        )
        if vars_path:
            values = _mapping(vars_path)
            inherited.update(values)
            suite.variable_locations = {(key,): SourceLocation(vars_path) for key in values}
        suite.variables = _resolve_variables(inherited)
        for path in sorted(suite.path.iterdir()):
            if path.suffix not in (".yaml", ".yml") or not path.is_file():
                continue
            if layout.is_mgtest_resource(path):
                for data in _definitions(path, "resource", "resources"):
                    model.add_definition(suite, "resources", data, SourceLocation(path))
            elif layout.is_mgtest_test(path):
                previous_name = None
                for data in _definitions(path, "test", "tests"):
                    data = dict(data)
                    if previous_name is not None:
                        dependencies = list(data.get("depends_on", []))
                        prerequisite = f"tests.{previous_name}"
                        if prerequisite not in dependencies:
                            dependencies.append(prerequisite)
                        data["depends_on"] = dependencies
                    definition = model.add_definition(suite, "tests", data, SourceLocation(path))
                    previous_name = definition.name
    _load_suite_manifests(model, layout)
    if not any(suite.tests for suite in model.suites.values()):
        raise ValueError(f"No tests defined in {root}")
    logger.info(
        "Loaded project %s with %d suites and %d definitions",
        root,
        len(model.suites),
        len(model.definitions),
    )
    return model


def _load_suite_manifests(model: ProjectModel, layout: ProjectLayout) -> None:
    """Load ``s_*.yaml`` groups after every definition has been discovered once."""
    manifests = sorted(
        path
        for path in model.root.rglob("s_*.y*ml")
        if layout.is_mgtest_suite_document(path) and layout.is_discoverable_directory(path.parent)
    )
    for path in manifests:
        identifier = path.with_suffix("").relative_to(model.root).as_posix()
        if identifier in model.suites:
            raise ProjectError(
                f"Suite manifest '{path.name}' conflicts with suite directory '{identifier}'",
                SourceLocation(path),
            )
        parent = path.parent.relative_to(model.root).as_posix() or "."
        if parent not in model.suites:
            raise ProjectError(
                "Suite manifests must be inside the project root or an s_* suite directory",
                SourceLocation(path),
            )
        members = _suite_members(_mapping(path), model, path)
        suite = Suite(identifier, path.parent, parent, test_members=members)
        model.suites[identifier] = suite
        model.suites[parent].children.append(identifier)


def _suite_members(data: dict, model: ProjectModel, path: Path) -> tuple[str, ...]:
    values = data.get("tests")
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ProjectError(
            "Suite manifest requires a 'tests' list of check selectors", SourceLocation(path)
        )
    if set(data) != {"tests"}:
        raise ProjectError("Suite manifest only supports the 'tests' field", SourceLocation(path))
    members: list[str] = []
    for selector in values:
        matches = _suite_member_matches(model, selector)
        if not matches:
            raise ProjectError(
                f"Unknown check '{selector}' in suite manifest", SourceLocation(path)
            )
        if len(matches) > 1:
            choices = ", ".join(matches)
            raise ProjectError(
                f"Check '{selector}' is ambiguous in suite manifest; use one of: {choices}",
                SourceLocation(path),
            )
        identity = matches[0]
        if identity not in members:
            members.append(identity)
    return tuple(members)


def _suite_member_matches(model: ProjectModel, selector: str) -> list[str]:
    if parsed := split_check_selector(selector):
        suite, name = parsed
        return [
            identity
            for identity, definition in model.definitions.items()
            if definition.kind == "tests" and definition.suite == suite and definition.name == name
        ]
    return [
        identity
        for identity, definition in model.definitions.items()
        if definition.kind == "tests" and definition.name == selector
    ]


def _mapping(path: Path) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML document must be a mapping: {path}")
    return data


def _definitions(path: Path, singular: str, plural: str) -> list[dict]:
    data = _mapping(path)
    value = data.get(plural, data.get(singular, [data]))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise ValueError(f"'{plural}' must be a mapping or sequence in {path}")


def _resolve_variables(values: dict) -> dict:
    """Resolve ordinary variables with OmegaConf, retaining execution references.

    Resource and test references are evaluated by the compiler after its dependency
    graph exists.  They must therefore survive this earlier configuration pass.
    """
    protected: dict[str, str] = {}

    def protect(value):
        if isinstance(value, dict):
            return {key: protect(item) for key, item in value.items()}
        if isinstance(value, list):
            return [protect(item) for item in value]
        if not isinstance(value, str):
            return value

        def replace(match):
            placeholder = f"__mgtest_execution_reference_{len(protected)}__"
            protected[placeholder] = match.group(0)
            return placeholder

        return _PROTECTED_EXPRESSION.sub(replace, value)

    def restore(value):
        if isinstance(value, dict):
            return {key: restore(item) for key, item in value.items()}
        if isinstance(value, list):
            return [restore(item) for item in value]
        if not isinstance(value, str):
            return value
        for placeholder, expression in protected.items():
            value = value.replace(placeholder, expression)
        return value

    try:
        config = OmegaConf.create({"vars": protect(values)})
        return restore(OmegaConf.to_container(config.vars, resolve=True))
    except Exception as error:
        raise ValueError(f"Unable to resolve variables: {error}") from error
