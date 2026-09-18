"""Editor-independent source model. Loading a model never instantiates plugins."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceLocation:
    path: Path
    line: int = 1
    column: int = 1
    end_line: int = 1
    end_column: int = 1

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column}"


class ProjectError(ValueError):
    def __init__(self, message: str, source: SourceLocation):
        self.message = message
        self.source = source
        super().__init__(f"{source}: {message}")


@dataclass
class Definition:
    id: str
    kind: Literal["resources", "tests"]
    name: str
    suite: str
    data: dict[str, Any]
    source: SourceLocation
    locations: dict[tuple, SourceLocation] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()

    def location(self, path: tuple = ()) -> SourceLocation:
        while path:
            if path in self.locations:
                return self.locations[path]
            path = path[:-1]
        return self.source


@dataclass
class Suite:
    id: str
    path: Path
    parent: str | None
    children: list[str] = field(default_factory=list)
    resources: dict[str, str] = field(default_factory=dict)
    tests: dict[str, str] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    variable_locations: dict[tuple, SourceLocation] = field(default_factory=dict)
    test_members: tuple[str, ...] | None = None


@dataclass
class ProjectModel:
    root: Path
    suites: dict[str, Suite]
    definitions: dict[str, Definition]
    selection: str = "."
    selected_tests: frozenset[str] | None = None
    documents: dict[Path, str] = field(default_factory=dict)

    def ancestors(self, suite: str):
        while suite is not None:
            node = self.suites[suite]
            yield node
            suite = node.parent

    def visible(self, suite: str, kind: str) -> dict[str, str]:
        result = {}
        for node in self.ancestors(suite):
            for name, identity in getattr(node, kind).items():
                result.setdefault(name, identity)
        return result

    def variable_owner(self, suite: str, name: str) -> Suite:
        for node in self.ancestors(suite):
            if name in node.variables:
                return node
        raise KeyError(name)

    def contains_suite(self, ancestor: str, descendant: str) -> bool:
        return any(node.id == ancestor for node in self.ancestors(descendant))

    def tests_in_selection(self, suite: str) -> frozenset[str]:
        """Return checks selected by a directory suite or suite manifest."""
        selected = self.suites[suite]
        if selected.test_members is not None:
            return frozenset(selected.test_members)
        return frozenset(
            identity
            for identity, definition in self.definitions.items()
            if definition.kind == "tests" and self.contains_suite(suite, definition.suite)
        )

    def add_definition(self, suite: Suite, kind: str, data: dict, source, locations=None):
        data = dict(data)
        depends_on = data.pop("depends_on", [])
        valid_dependencies = isinstance(depends_on, list) and all(
            isinstance(item, str) for item in depends_on
        )
        if not valid_dependencies:
            raise ProjectError("'depends_on' must be a list of definition names", source)
        name = data.get("name")
        if not isinstance(name, str) or not name or any(c in name for c in ".:{}"):
            raise ProjectError(
                "Definition names must be nonempty and cannot contain . : { }", source
            )
        namespace = getattr(suite, kind)
        if name in namespace:
            previous = self.definitions[namespace[name]]
            raise ProjectError(
                f"Duplicate {kind} name '{name}'; first defined at {previous.source}", source
            )
        identity = f"{suite.id}::{kind}.{name}"
        definition = Definition(
            identity, kind, name, suite.id, data, source, locations or {}, tuple(depends_on)
        )
        self.definitions[identity] = definition
        namespace[name] = identity
        logger.debug("Added %s definition %s", kind, identity)
        return definition
