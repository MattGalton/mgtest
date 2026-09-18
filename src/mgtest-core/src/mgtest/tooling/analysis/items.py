"""Reusable LSP-shaped item builders for mgtest editor features."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin


class AnalysisItems:
    """Construct completion and documentation values without project access."""

    @staticmethod
    def field(name: str, field) -> dict[str, Any]:
        description = field.description or f"`{field.annotation}`"
        field_name = field.alias or name
        return {
            "label": field_name,
            "kind": 10,
            "detail": description,
            "documentation": {
                "kind": "markdown",
                "value": AnalysisItems.field_documentation(field_name, field),
            },
            "insertText": f"{field_name}: {AnalysisItems._default_insert_text(field)}",
        }

    @staticmethod
    def field_documentation(name: str, field) -> str:
        """Return the complete Markdown documentation for a model field."""
        documentation = [f"### `{name}`", "", field.description or "No description available."]
        documentation.extend(("", f"**Type:** `{AnalysisItems._type_name(field.annotation)}`"))
        if field.is_required():
            documentation.extend(("", "**Required:** yes"))
        elif field.default_factory is not None:
            factory = getattr(
                field.default_factory, "__name__", field.default_factory.__class__.__name__
            )
            documentation.extend(("", f"**Default:** a new `{factory}()` value"))
        else:
            documentation.extend(("", f"**Default:** `{AnalysisItems._value(field.default)}`"))
        if values := AnalysisItems._literal_values(field.annotation):
            rendered = ", ".join(f"`{AnalysisItems._value(value)}`" for value in values)
            documentation.extend(("", f"**Accepted values:** {rendered}"))
        if constraints := AnalysisItems._constraints(field.metadata):
            documentation.extend(("", f"**Constraints:** {'; '.join(constraints)}"))
        if examples := field.examples:
            rendered = ", ".join(f"`{AnalysisItems._value(example)}`" for example in examples)
            documentation.extend(("", f"**Examples:** {rendered}"))
        return "\n".join(documentation)

    @staticmethod
    def _type_name(annotation) -> str:
        origin = get_origin(annotation)
        if origin is Literal:
            values = ", ".join(AnalysisItems._value(value) for value in get_args(annotation))
            return f"Literal[{values}]"
        if origin in (Union, UnionType):
            return " | ".join(
                AnalysisItems._type_name(argument) for argument in get_args(annotation)
            )
        if origin:
            origin_name = getattr(origin, "__name__", str(origin).replace("typing.", ""))
            arguments = ", ".join(
                AnalysisItems._type_name(argument) for argument in get_args(annotation)
            )
            return f"{origin_name}[{arguments}]"
        return getattr(annotation, "__name__", str(annotation).replace("typing.", ""))

    @staticmethod
    def _literal_values(annotation) -> tuple[Any, ...]:
        return get_args(annotation) if get_origin(annotation) is Literal else ()

    @staticmethod
    def _default_insert_text(field) -> str:
        if field.is_required():
            return ""
        if field.default_factory is not None:
            factory = getattr(field.default_factory, "__name__", "")
            return {"dict": "{}", "list": "[]", "set": "[]"}.get(factory, "")
        return AnalysisItems._value(field.default)

    @staticmethod
    def _value(value: Any) -> str:
        if isinstance(value, Enum):
            value = value.value
        if value is None:
            return "null"
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, str | Path):
            return f'"{value}"'
        return str(value)

    @staticmethod
    def _constraints(metadata) -> list[str]:
        constraints = []
        names = {
            "gt": "greater than",
            "ge": "greater than or equal to",
            "lt": "less than",
            "le": "less than or equal to",
            "multiple_of": "a multiple of",
            "min_length": "minimum length",
            "max_length": "maximum length",
            "max_digits": "at most",
            "decimal_places": "at most",
        }
        for item in metadata:
            for attribute, label in names.items():
                if (value := getattr(item, attribute, None)) is not None:
                    suffix = (
                        " decimal digits"
                        if attribute == "max_digits"
                        else " decimal places" if attribute == "decimal_places" else ""
                    )
                    constraints.append(f"{label} `{AnalysisItems._value(value)}`{suffix}")
            if getattr(item, "allow_inf_nan", True) is False:
                constraints.append("a finite number")
        return constraints

    @staticmethod
    def type_key() -> dict[str, Any]:
        return {
            "label": "type",
            "kind": 10,
            "detail": "mgtest definition type",
            "documentation": {
                "kind": "markdown",
                "value": "Choose the resource or test type this YAML document defines.",
            },
            "insertText": "type: ",
        }

    @staticmethod
    def type(name: str, cls: type, kind: str, prefix: str) -> dict[str, Any]:
        documentation = (cls.__doc__ or f"mgtest {kind} type").strip()
        summary = documentation.splitlines()[0]
        indent = re.match(r"\s*", prefix).group()
        required = [
            field_name
            for field_name, field in cls.model_fields.items()
            if field_name != "type" and field.is_required()
        ]
        snippet = name + "".join(
            f"\n{indent}{field_name}: ${{{index}}}"
            for index, field_name in enumerate(required, start=1)
        )
        return {
            "label": name,
            "kind": 12,
            "detail": f"mgtest {kind} type — {summary}",
            "documentation": {"kind": "markdown", "value": documentation},
            "insertText": snippet,
            "insertTextFormat": 2,
        }

    @staticmethod
    def definition_documentation(definition) -> dict[str, str]:
        return {
            "kind": "markdown",
            "value": (
                f"Visible mgtest **{definition.kind[:-1]}** `{definition.name}`.\n\n"
                f"Type: `{definition.data.get('type', 'unknown')}`.\n\n"
                f"Defined in `{definition.source.path}`."
            ),
        }

    @staticmethod
    def variable_documentation(name: str, source) -> dict[str, str]:
        location = f"Defined in `{source.path}`." if source else "Inherited variable."
        return {"kind": "markdown", "value": f"mgtest variable `{name}`.\n\n{location}"}

    @staticmethod
    def output(kind: str, name: str, cls, field_name: str, field) -> dict[str, Any]:
        output_name = field.alias or field_name
        description = field.description or f"`{field.annotation}`"
        type_documentation = (cls.__doc__ or "").strip()
        documentation = (
            f"Output `{kind}.{name}.outputs.{output_name}` from `{cls.__name__}`.\n\n"
            f"{description}"
        )
        if type_documentation:
            documentation += f"\n\n{type_documentation}"
        return {
            "label": output_name,
            "kind": 5,
            "detail": description,
            "documentation": {"kind": "markdown", "value": documentation},
        }
