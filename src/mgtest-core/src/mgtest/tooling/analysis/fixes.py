"""Quick fixes for common mgtest YAML diagnostics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from mgtest.project.layout import ProjectLayout

from .documents import definitions
from .types import REFERENCE_VALUE


class FixProvider:
    """Construct protocol-neutral workspace edits for common authoring mistakes."""

    _TYPE = re.compile(r"^\s*(?:-\s*)?type:\s*(?P<name>[^\s#]+)", re.MULTILINE)

    def __init__(self, context):
        self.context = context

    def actions(self, path: Path, source: str, selection: dict[str, Any]) -> list[dict[str, Any]]:
        if not ProjectLayout.is_mgtest_document(path):
            return []
        catalog = self.context.catalog_for(path)
        try:
            data = yaml.safe_load(source) or {}
        except yaml.YAMLError:
            return []
        if not isinstance(data, dict):
            return []
        return [
            *self._unknown_type_actions(path, source, selection, catalog),
            *self._missing_field_actions(path, source, data, catalog),
            *self._missing_dependency_actions(path, source, data),
        ]

    def _unknown_type_actions(self, path, source, selection, catalog):
        kind = ProjectLayout.definition_kind(path)
        registry = getattr(catalog, kind) if kind else {**catalog.resources, **catalog.tests}
        names = registry.keys()
        actions = []
        for match in self._TYPE.finditer(source):
            if match.group("name") in registry or not self._intersects(match, source, selection):
                continue
            for name in sorted(names):
                actions.append(
                    self._action(
                        path,
                        f"Replace with {name}",
                        source,
                        match.start("name"),
                        match.end("name"),
                        name,
                    )
                )
        return actions

    def _missing_field_actions(self, path, source, data, catalog):
        kind = ProjectLayout.definition_kind(path)
        if kind is None:
            return []
        actions = []
        type_matches = list(self._TYPE.finditer(source))
        for declared, match in zip(definitions(path, data)[0][1], type_matches, strict=False):
            cls = getattr(catalog, kind).get(declared.get("type"))
            if cls is None:
                continue
            line_start = source.rfind("\n", 0, match.start()) + 1
            line_end = source.find("\n", match.end())
            if line_end == -1:
                line_end = len(source)
            indent = re.match(r"\s*", source[line_start:]).group()
            if source[line_start + len(indent) :].startswith("- "):
                indent += "  "
            for name, field in cls.model_fields.items():
                field_name = field.alias or name
                if field.is_required() and field_name not in declared:
                    actions.append(
                        self._action(
                            path,
                            f"Add required field '{field_name}'",
                            source,
                            line_end,
                            line_end,
                            f"\n{indent}{field_name}: ",
                        )
                    )
        return actions

    def _missing_dependency_actions(self, path, source, data):
        declared = [item for _, items in definitions(path, data) for item in items]
        dependencies = {
            dependency
            for item in declared
            for dependency in item.get("depends_on", [])
            if isinstance(dependency, str)
        }
        actions = []
        for match in REFERENCE_VALUE.finditer(source):
            if match.group("output") is None:
                continue
            dependency = f"{match.group('kind')}.{match.group('name')}"
            if dependency in dependencies:
                continue
            actions.append(
                self._action(
                    path,
                    f"Add dependency '{dependency}'",
                    source,
                    len(source),
                    len(source),
                    f"\ndepends_on:\n  - {dependency}\n",
                )
            )
        return actions

    @staticmethod
    def _intersects(match, source, selection) -> bool:
        start = selection.get("start", {})
        end = selection.get("end", start)
        selected_start = FixProvider._offset(source, start)
        selected_end = FixProvider._offset(source, end)
        return selected_start <= match.end() and match.start() <= selected_end

    @staticmethod
    def _action(path, title, source, start, end, new_text):
        return {
            "title": title,
            "kind": "quickfix",
            "edit": {
                "changes": {
                    path.resolve().as_uri(): [
                        {"range": FixProvider._range(source, start, end), "newText": new_text}
                    ]
                }
            },
        }

    @staticmethod
    def _range(source: str, start: int, end: int) -> dict[str, dict[str, int]]:
        return {
            "start": FixProvider._position(source, start),
            "end": FixProvider._position(source, end),
        }

    @staticmethod
    def _position(source: str, offset: int) -> dict[str, int]:
        line = source[:offset].count("\n")
        return {"line": line, "character": offset - source.rfind("\n", 0, offset) - 1}

    @staticmethod
    def _offset(source: str, position: dict[str, int]) -> int:
        lines = source.splitlines(keepends=True)
        line = position.get("line", 0)
        if line >= len(lines):
            return len(source)
        return sum(len(item) for item in lines[:line]) + position.get("character", 0)
