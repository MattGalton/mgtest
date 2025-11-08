"""Hover, definition, and reference providers for mgtest YAML documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from mgtest.project.layout import ProjectLayout

from .documents import definitions, name_range, nearest_type
from .items import AnalysisItems
from .types import REFERENCE, REFERENCE_VALUE


class NavigationProvider:
    """Resolve editor navigation requests against project and plugin metadata."""

    def __init__(self, context):
        self.context = context

    def hover(self, path: Path, source: str, line: int, character: int) -> str | None:
        if not ProjectLayout.is_mgtest_document(path):
            return None
        catalog = self.context.catalog_for(path)
        if value := self._reference_hover(path, source, line, character, catalog):
            return value
        word = self._word_at(source, line, character)
        cls = catalog.resources.get(word) or catalog.tests.get(word)
        if cls:
            return cls.__doc__ or f"mgtest {word} definition"
        try:
            data = yaml.safe_load(source) or {}
        except yaml.YAMLError:
            return None
        kind = ProjectLayout.yaml_specialisation_kind(path)
        type_name = data.get("specialises") if kind else nearest_type(data)
        registry = getattr(catalog, kind) if kind else None
        cls = (
            registry.get(type_name)
            if registry
            else (catalog.resources.get(type_name) or catalog.tests.get(type_name))
        )
        if cls and word in cls.model_fields:
            field = cls.model_fields[word]
            return AnalysisItems.field_documentation(field.alias or word, field)
        return None

    def definitions(self, path: Path, source: str, line: int, character: int) -> list[Path]:
        if not ProjectLayout.is_mgtest_document(path):
            return []
        lines = source.splitlines()
        if line >= len(lines):
            return []
        for match in REFERENCE_VALUE.finditer(lines[line]):
            if match.start() <= character <= match.end():
                target = self._reference_definition(path, match)
                return [target] if target else []
        for match in REFERENCE.finditer(lines[line]):
            if match.start() <= character <= match.end():
                target = (
                    self.context.project_definitions(path)
                    .get(match.group("kind"), {})
                    .get(match.group("name"))
                )
                return [target] if target else []
        word = self._word_at(source, line, character)
        catalog = self.context.catalog_for(path)
        cls = catalog.resources.get(word) or catalog.tests.get(word)
        target = getattr(cls, "__mgtest_specialisation_source__", None) if cls else None
        return [target] if isinstance(target, Path) else []

    def references(
        self, path: Path, source: str, line: int, character: int
    ) -> list[dict[str, Any]]:
        if not ProjectLayout.is_mgtest_document(path):
            return []
        selected = self._reference_at(source, line, character)
        if selected is None or (target := self._reference_definition(path, selected)) is None:
            return []
        context = self.context.project_context(path)
        if context is None:
            return []
        model, _ = context
        documents = self.context.project_documents(model.root)
        documents[path] = source
        usages = []
        for document_path in sorted(
            documents,
            key=lambda candidate: (candidate.resolve() != path.resolve(), candidate.as_posix()),
        ):
            document_source = documents[document_path]
            for usage_line, text in enumerate(document_source.splitlines()):
                for match in REFERENCE_VALUE.finditer(text):
                    if self._reference_definition_from_model(model, document_path, match) == target:
                        usages.append(
                            {
                                "uri": document_path.as_uri(),
                                "range": {
                                    "start": {"line": usage_line, "character": match.start()},
                                    "end": {"line": usage_line, "character": match.end()},
                                },
                            }
                        )
        return usages

    def symbols(self, path: Path, source: str) -> list[dict[str, Any]]:
        """Return document symbols for declared definitions and specialisations."""
        if not ProjectLayout.is_mgtest_document(path):
            return []
        try:
            data = yaml.safe_load(source) or {}
        except yaml.YAMLError:
            return []
        if not isinstance(data, dict):
            return []
        if kind := ProjectLayout.yaml_specialisation_kind(path):
            parent = data.get("specialises")
            if not isinstance(parent, str):
                return []
            item = {
                "name": path.stem,
                "kind": 5 if kind == "resources" else 6,
                "detail": f"specialises {parent}",
                "range": name_range(source, "specialises"),
                "selectionRange": name_range(source, "specialises"),
            }
            return [item]
        return [
            {
                "name": name,
                "kind": 5 if kind == "resources" else 6,
                "detail": definition.get("type", kind[:-1]),
                "range": name_range(source, name),
                "selectionRange": name_range(source, name),
            }
            for kind, declared in definitions(path, data)
            for definition in declared
            if isinstance(name := definition.get("name"), str)
        ]

    def _reference_hover(self, path, source, line, character, catalog) -> str | None:
        match = self._reference_at(source, line, character)
        context = self.context.project_context(path)
        if match is None or context is None:
            return None
        model, suite = context
        if variable := match.group("variable"):
            location = self.context.variable_location(model, suite, variable)
            return AnalysisItems.variable_documentation(variable, location)["value"]
        kind, name = match.group("kind"), match.group("name")
        definition_id = self.context.visible_definitions(model, suite, kind, path).get(name)
        if definition_id is None:
            return None
        definition = model.definitions[definition_id]
        if not (output := match.group("output")):
            return AnalysisItems.definition_documentation(definition)["value"]
        cls = getattr(catalog, kind).get(definition.data.get("type"))
        output_model = cls.output_model() if cls else None
        field = output_model.model_fields.get(output) if output_model else None
        return (
            AnalysisItems.output(kind, name, cls, output, field)["documentation"]["value"]
            if field
            else None
        )

    def _reference_definition(self, path: Path, match: re.Match[str]) -> Path | None:
        context = self.context.project_context(path)
        return self._reference_definition_from_model(context[0], path, match) if context else None

    def _reference_definition_from_model(
        self, model, path: Path, match: re.Match[str]
    ) -> Path | None:
        suite = next(
            (
                suite
                for suite in model.suites.values()
                if suite.path.resolve() == path.resolve().parent
            ),
            None,
        )
        if suite is None:
            return None
        if variable := match.group("variable"):
            location = self.context.variable_location(model, suite, variable)
            return location.path if location else None
        kind, name = match.group("kind"), match.group("name")
        definition_id = self.context.visible_definitions(model, suite, kind, path).get(name)
        return model.definitions[definition_id].source.path if definition_id else None

    @staticmethod
    def _reference_at(source: str, line: int, character: int):
        lines = source.splitlines()
        if line >= len(lines):
            return None
        return next(
            (
                match
                for match in REFERENCE_VALUE.finditer(lines[line])
                if match.start() <= character <= match.end()
            ),
            None,
        )

    @staticmethod
    def _word_at(source: str, line: int, character: int) -> str:
        lines = source.splitlines()
        if line >= len(lines):
            return ""
        for word in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", lines[line]):
            if word.start() <= character <= word.end():
                return word.group()
        return ""
