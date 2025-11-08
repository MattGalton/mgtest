from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from mgtest.engine.project.model import ProjectError, SourceLocation

EXPRESSION = re.compile(r"\$\{([^{}]+)\}")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Reference:
    expression: str
    source: SourceLocation


@dataclass(frozen=True)
class ReferenceBinding:
    reference: Reference
    owner: str
    owner_path: tuple
    target: str
    target_path: tuple
    runtime: bool


@dataclass(frozen=True)
class OutputReference:
    target: str
    path: tuple[str, ...]
    annotation: Any
    source: SourceLocation


@dataclass(frozen=True)
class Interpolation:
    parts: tuple[Any, ...]


def parse(value, source):
    if not isinstance(value, str) or "${" not in value:
        return value
    matches = list(EXPRESSION.finditer(value))
    if not matches or "${" in EXPRESSION.sub("", value):
        raise ProjectError("Malformed reference expression", source)
    if len(matches) == 1 and matches[0].span() == (0, len(value)):
        logger.debug("Parsed reference at %s", source)
        return Reference(matches[0][1], source)
    parts = []
    start = 0
    for match in matches:
        parts.extend((value[start : match.start()], Reference(match[1], source)))
        start = match.end()
    parts.append(value[start:])
    logger.debug("Parsed interpolation with %d references at %s", len(matches), source)
    return Interpolation(tuple(parts))


def output_references(value):
    if isinstance(value, OutputReference):
        yield value
    elif isinstance(value, Interpolation):
        for part in value.parts:
            yield from output_references(part)
    elif isinstance(value, dict):
        for item in value.values():
            yield from output_references(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from output_references(item)


def resolve(value, lookup):
    if isinstance(value, OutputReference):
        return lookup(value)
    if isinstance(value, Interpolation):
        return "".join(str(resolve(part, lookup)) for part in value.parts)
    if isinstance(value, dict):
        return {key: resolve(item, lookup) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, lookup) for item in value]
    return value


def get_path(value, path):
    for key in path:
        if isinstance(value, dict):
            value = value[key]
        elif isinstance(value, list | tuple):
            value = value[int(key)]
        else:
            value = getattr(value, key)
    return value
