"""Completion provider for mgtest YAML documents."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from mgtest.project.layout import ProjectLayout

from .documents import nearest_type
from .items import AnalysisItems
from .types import OMEGACONF_RESOLVERS


class CompletionProvider:
    def __init__(self, context):
        self.context = context

    def complete(self, path: Path, source: str, line: int, character: int) -> list[dict]:
        if not ProjectLayout.is_mgtest_document(path):
            return []
        catalog = self.context.catalog_for(path)
        prefix = source.splitlines()[line][:character] if line < len(source.splitlines()) else ""
        if ProjectLayout.definition_kind(path) and self._yaml(source) == {}:
            return [AnalysisItems.type_key()]
        if "${" in prefix:
            return self.references(path, prefix, catalog)
        kind = ProjectLayout.yaml_specialisation_kind(path)
        if kind and prefix.lstrip().startswith("specialises:"):
            return self.types(catalog, kind, prefix)
        if prefix.lstrip().startswith("type:"):
            kind = ProjectLayout.definition_kind(path)
            return (
                self.types(catalog, kind, prefix)
                if kind
                else [
                    AnalysisItems.type(n, c, "definition", prefix)
                    for n, c in sorted({**catalog.resources, **catalog.tests}.items())
                ]
            )
        data = self._yaml(source) or self._yaml_without_active_line(source, line)
        if data is None:
            return []
        name = data.get("specialises") if kind else nearest_type(data)
        registry = getattr(catalog, kind) if kind else None
        cls = (
            registry.get(name)
            if registry
            else catalog.resources.get(name) or catalog.tests.get(name)
        )
        if not cls:
            return []
        key = self.key(prefix)
        if key == "depends_on":
            return self.dependencies(path)
        if key and key not in {"name", "type"}:
            return self.values(path, catalog)
        if not self._is_field_context(source, line):
            return []
        return self.fields(cls, source)

    def types(self, catalog, kind, prefix):
        return [
            AnalysisItems.type(n, c, kind[:-1], prefix)
            for n, c in sorted(getattr(catalog, kind).items())
        ]

    def fields(self, cls, source):
        existing = set(re.findall(r"^\s*(?:-\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:", source, re.M))
        return [
            AnalysisItems.field(n, f)
            for n, f in cls.model_fields.items()
            if (f.alias or n) not in existing
        ]

    def references(self, path, prefix, catalog):
        expression = prefix[prefix.rfind("${") + 2 :].rstrip("}'\" ")
        if "mgtest:".startswith(expression) or not expression:
            return [
                {"label": k, "kind": 6, "detail": f"mgtest {k} reference"}
                for k in ("vars", "resources", "tests")
            ] + self.omegaconf(expression)
        if expression.startswith("oc"):
            return self.omegaconf(expression)
        expression = expression.removeprefix("mgtest:")
        context = self.context.project_context(path)
        if not context:
            return []
        model, suite = context
        parts = expression.split(".")
        if "vars".startswith(expression):
            return [
                {"label": n, "kind": 6, "detail": "mgtest variable"}
                for n in sorted(suite.variables)
            ]
        if parts[0] == "vars":
            return [self.variable(model, suite, n) for n in sorted(suite.variables)]
        if parts[0] not in {"resources", "tests"}:
            return []
        visible = self.context.visible_definitions(model, suite, parts[0], path)
        if len(parts) == 1 or len(parts) == 2 and parts[1] not in visible:
            return [
                {
                    "label": n,
                    "kind": 6,
                    "detail": f"visible mgtest {parts[0][:-1]}",
                    "documentation": AnalysisItems.definition_documentation(model.definitions[i]),
                }
                for n, i in sorted(visible.items())
            ]
        definition = model.definitions[visible[parts[1]]]
        if len(parts) < 3 or parts[2] != "outputs":
            return [{"label": "outputs", "kind": 5, "detail": "mgtest outputs"}]
        cls = getattr(catalog, definition.kind).get(definition.data.get("type"))
        outputs = cls.output_model() if cls else None
        return [
            AnalysisItems.output(definition.kind, definition.name, cls, n, f)
            for n, f in (outputs.model_fields.items() if outputs else ())
        ]

    def dependencies(self, path):
        context = self.context.project_context(path)
        if not context:
            return []
        model, suite = context
        return [
            {
                "label": f"{k}.{n}",
                "kind": 6,
                "detail": f"visible mgtest {k[:-1]}",
                "documentation": AnalysisItems.definition_documentation(model.definitions[i]),
            }
            for k in ("resources", "tests")
            for n, i in sorted(self.context.visible_definitions(model, suite, k, path).items())
        ]

    def values(self, path, catalog):
        context = self.context.project_context(path)
        if not context:
            return []
        model, suite = context
        items = [self.variable(model, suite, n, f"${{vars.{n}}}") for n in sorted(suite.variables)]
        for k in ("resources", "tests"):
            for n, i in self.context.visible_definitions(model, suite, k, path).items():
                d = model.definitions[i]
                cls = getattr(catalog, k).get(d.data.get("type"))
                outputs = cls.output_model() if cls else None
                for oname, field in outputs.model_fields.items() if outputs else ():
                    item = AnalysisItems.output(k, n, cls, oname, field)
                    item["label"] = f"${{mgtest:{k}.{n}.outputs.{field.alias or oname}}}"
                    items.append(item)
        return items

    def variable(self, model, suite, name, label=None):
        return {
            "label": label or name,
            "kind": 6,
            "detail": "mgtest variable",
            "documentation": AnalysisItems.variable_documentation(
                name, self.context.variable_location(model, suite, name)
            ),
        }

    @staticmethod
    def key(prefix):
        m = re.match(r"^\s*(?:-\s*)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:", prefix)
        return m.group("key") if m else None

    @staticmethod
    def _yaml(source):
        try:
            return yaml.safe_load(source) or {}
        except yaml.YAMLError:
            return None

    @classmethod
    def _yaml_without_active_line(cls, source: str, line: int):
        """Parse completed context when the current line is an unfinished YAML key."""
        lines = source.splitlines(keepends=True)
        if line >= len(lines):
            return None
        return cls._yaml("".join(lines[:line] + lines[line + 1 :]))

    @staticmethod
    def _is_field_context(source: str, line: int) -> bool:
        """Whether the active line can declare a key beside its type declaration."""
        lines = source.splitlines()
        if line == len(lines):
            lines.append("")
        if line >= len(lines) or not re.fullmatch(
            r"\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*)?", lines[line]
        ):
            return False
        current_indent = len(lines[line]) - len(lines[line].lstrip())
        type_line = re.compile(r"^(?P<indent>\s*)(?P<item>-\s*)?(?:type|specialises)\s*:\s*\S")
        for previous in reversed(lines[:line]):
            if match := type_line.match(previous):
                field_indent = len(match.group("indent")) + (2 if match.group("item") else 0)
                return current_indent == field_indent
        return False

    @staticmethod
    def omegaconf(expression):
        return [
            {
                "label": n,
                "kind": 3,
                "detail": "OmegaConf resolver",
                "documentation": {"kind": "markdown", "value": d},
            }
            for n, d in OMEGACONF_RESOLVERS.items()
            if n.startswith(expression.rstrip(":"))
        ]
