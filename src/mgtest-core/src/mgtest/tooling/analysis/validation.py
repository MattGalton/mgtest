"""Validation provider for mgtest YAML documents."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from mgtest.engine.plugin.yaml_specialization import specialisation_defaults, specialisation_parent
from mgtest.engine.project.compiler import ProjectCompiler
from mgtest.engine.project.model import ProjectError, SourceLocation
from mgtest.engine.project.validation import validate_fields
from mgtest.project.layout import ProjectLayout

from .documents import definitions
from .types import REFERENCE_VALUE, Diagnostic


class ValidationProvider:
    """Validate YAML syntax, declarations, and project references."""

    def __init__(self, context):
        self.context = context

    def analyse(self, path: Path, source: str) -> list[Diagnostic]:
        if not ProjectLayout.is_mgtest_document(path):
            return []
        catalog = self.context.catalog_for(path)
        try:
            data = yaml.safe_load(source) or {}
        except yaml.MarkedYAMLError as error:
            mark = error.problem_mark
            if mark is None:
                return [Diagnostic(error.problem or "Invalid YAML")]
            return [Diagnostic(error.problem or "Invalid YAML", mark.line, mark.column)]
        if not isinstance(data, dict):
            return [Diagnostic("YAML document must be a mapping")]
        if kind := ProjectLayout.yaml_specialisation_kind(path):
            return self._validate_specialisation(path, kind, data, catalog)
        if ProjectLayout.is_mgtest_suite_document(path):
            if (
                set(data) != {"tests"}
                or not isinstance(data.get("tests"), list)
                or not all(isinstance(value, str) for value in data["tests"])
            ):
                return [
                    Diagnostic("Suite manifest requires only a 'tests' list of check selectors")
                ]
            return []
        diagnostics = []
        for kind, declared in definitions(path, data):
            diagnostics.extend(self._validate_definition(kind, declared, catalog))
        diagnostics.extend(self._validate_references(path, source, catalog))
        diagnostics.extend(self._validate_dependency_cycle(path, source, catalog))
        return diagnostics

    def _validate_definition(self, kind: str, declared: list[dict], catalog) -> list[Diagnostic]:
        if not declared:
            return [Diagnostic(f"'{kind}' must be a mapping or sequence of mappings")]
        diagnostics = []
        registry = getattr(catalog, kind)
        for data in declared:
            type_name = data.get("type")
            if not isinstance(type_name, str):
                diagnostics.append(Diagnostic("Every definition requires a literal string 'type'"))
                continue
            cls = registry.get(type_name)
            if cls is None:
                diagnostics.append(Diagnostic(f"Unknown {kind[:-1]} type '{type_name}'"))
                continue
            try:
                validate_fields(
                    {key: value for key, value in data.items() if key != "depends_on"},
                    cls,
                    lambda _: SourceLocation(Path("<editor>")),
                )
            except (ProjectError, ValidationError, ValueError) as error:
                diagnostics.append(Diagnostic(str(error)))
        return diagnostics

    def _validate_references(self, path: Path, source: str, catalog) -> list[Diagnostic]:
        diagnostics = []
        for line, text in enumerate(source.splitlines()):
            for match in REFERENCE_VALUE.finditer(text):
                if message := self._reference_diagnostic(path, match, catalog):
                    diagnostics.append(
                        Diagnostic(
                            message, line, match.start(), line, match.end(), code="reference"
                        )
                    )
        return diagnostics

    def _reference_diagnostic(self, path: Path, match: re.Match[str], catalog) -> str | None:
        context = self.context.project_context(path)
        if context is None:
            if match.group("variable"):
                return None
            kind, name = match.group("kind"), match.group("name")
            return (
                None
                if name in self.context.project_definitions(path).get(kind, {})
                else f"Unknown or invisible {kind}.{name}"
            )
        model, suite = context
        if variable := match.group("variable"):
            return (
                None
                if self.context.variable_location(model, suite, variable)
                else f"Unknown or invisible variable '{variable}'"
            )
        kind, name = match.group("kind"), match.group("name")
        definition_id = self.context.visible_definitions(model, suite, kind, path).get(name)
        if definition_id is None:
            return f"Unknown or invisible {kind}.{name}"
        output = match.group("output")
        if output is None:
            return None
        definition = model.definitions[definition_id]
        cls = getattr(catalog, kind).get(definition.data.get("type"))
        output_model = cls.output_model() if cls else None
        fields = output_model.model_fields if output_model else {}
        if any((field.alias or field_name) == output for field_name, field in fields.items()):
            return None
        return f"Unknown output '{output}' on {kind}.{name}"

    def _validate_dependency_cycle(self, path: Path, source: str, catalog) -> list[Diagnostic]:
        """Report a project dependency cycle on the ``depends_on`` declaration that closes it."""
        context = self.context.project_context(path)
        if context is None:
            return []
        model, _ = context
        try:
            ProjectCompiler(catalog).compile(model)
        except ProjectError as error:
            if (
                not error.message.startswith("Dependency cycle:")
                or error.source.path.resolve() != path.resolve()
            ):
                return []
            return [self._cycle_diagnostic(error.message, source)]
        return []

    @staticmethod
    def _cycle_diagnostic(message: str, source: str) -> Diagnostic:
        match = re.search(r"^\s*depends_on\s*:", source, re.MULTILINE)
        if match is None:
            return Diagnostic(message, code="cycle")
        line = source[: match.start()].count("\n")
        character = match.start() - source.rfind("\n", 0, match.start()) - 1
        return Diagnostic(
            message, line, character, line, match.end() - match.start() + character, code="cycle"
        )

    @staticmethod
    def _validate_specialisation(path: Path, kind: str, data: dict, catalog) -> list[Diagnostic]:
        try:
            parent = specialisation_parent(path, data, getattr(catalog, kind), kind)
            specialisation_defaults(path, data, parent)
        except ValueError as error:
            return [Diagnostic(str(error))]
        return []
