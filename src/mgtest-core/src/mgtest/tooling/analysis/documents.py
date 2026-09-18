"""YAML document structure shared by analysis providers."""

from __future__ import annotations

import re
from pathlib import Path

from mgtest.project.layout import ProjectLayout


def definitions(path: Path, data: dict) -> list[tuple[str, list[dict]]]:
    """Return the definitions declared by a resource or test document."""
    kind = ProjectLayout.definition_kind(path)
    if kind is None:
        return []
    value = data.get(kind, data.get(kind[:-1], [data]))
    values = [value] if isinstance(value, dict) else value
    return [
        (
            kind,
            (
                values
                if isinstance(values, list) and all(isinstance(item, dict) for item in values)
                else []
            ),
        )
    ]


def nearest_type(data: object) -> str | None:
    """Return the first literal ``type`` declared in a YAML value."""
    if isinstance(data, dict):
        if isinstance(data.get("type"), str):
            return data["type"]
        for value in data.values():
            if found := nearest_type(value):
                return found
    if isinstance(data, list):
        for value in data:
            if found := nearest_type(value):
                return found
    return None


def name_range(source: str, name: str) -> dict[str, dict[str, int]]:
    for line, text in enumerate(source.splitlines()):
        match = re.search(rf"\bname:\s*{re.escape(name)}\b", text)
        if match:
            start = match.start() + match.group().rfind(name)
            return {
                "start": {"line": line, "character": start},
                "end": {"line": line, "character": start + len(name)},
            }
    return {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}
