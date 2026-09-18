"""Validate authored values without replacing runtime references with fake values."""

from __future__ import annotations

import logging
import types
from functools import reduce
from operator import or_
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel, TypeAdapter

from mgtest.engine.project.model import ProjectError
from mgtest.engine.project.references import Interpolation, OutputReference, output_references

logger = logging.getLogger(__name__)


def unwrap(annotation):
    return unwrap(get_args(annotation)[0]) if get_origin(annotation) is Annotated else annotation


def compatible(source, target):
    source, target = unwrap(source), unwrap(target)
    if source is Any or target is Any or source == target:
        return True
    so, to = get_origin(source), get_origin(target)
    if so in (Union, types.UnionType):
        return any(compatible(arg, target) for arg in get_args(source))
    if to in (Union, types.UnionType):
        return any(compatible(source, arg) for arg in get_args(target))
    if so is Literal:
        return any(compatible(type(value), target) for value in get_args(source))
    if to is Literal:
        return any(compatible(source, type(value)) for value in get_args(target))
    if so or to:
        if so != to:
            return False
        return all(
            compatible(a, b) for a, b in zip(get_args(source), get_args(target), strict=False)
        )
    if source is int and target is float:
        return True
    return isinstance(source, type) and isinstance(target, type) and issubclass(source, target)


def output_annotation(annotation, path, source):
    for key in path:
        annotation = unwrap(annotation)
        origin, args = get_origin(annotation), get_args(annotation)
        if annotation is Any:
            return Any
        if origin in (Union, types.UnionType):
            alternatives = []
            for item in args:
                try:
                    alternatives.append(output_annotation(item, (key,), source))
                except ProjectError:
                    pass
            if not alternatives:
                raise ProjectError(f"Unknown output field '{key}'", source)
            annotation = reduce(or_, alternatives)
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if key not in annotation.model_fields:
                raise ProjectError(f"Unknown output field '{key}' on {annotation.__name__}", source)
            annotation = annotation.model_fields[key].rebuild_annotation()
        elif origin is dict:
            annotation = args[1]
        elif origin in (list, tuple) and key.isdigit():
            annotation = args[0] if origin is list or args[-1] is Ellipsis else args[int(key)]
        else:
            raise ProjectError(f"Cannot access output field '{key}' on {annotation}", source)
    return annotation


def validate_value(value, annotation, source):
    if not any(output_references(value)):
        TypeAdapter(annotation).validate_python(value)
        return
    bare = unwrap(annotation)
    if isinstance(value, OutputReference):
        if not compatible(value.annotation, bare):
            raise ProjectError(
                f"Output type {value.annotation} is incompatible with {bare}", value.source
            )
        return
    if isinstance(value, Interpolation):
        if not compatible(str, bare):
            raise ProjectError(f"String interpolation is incompatible with {bare}", source)
        return
    origin, args = get_origin(bare), get_args(bare)
    if bare is Any:
        return
    if origin in (Union, types.UnionType):
        for alternative in args:
            try:
                validate_value(value, alternative, source)
                return
            except (ValueError, TypeError):
                pass
        raise ProjectError(f"Referenced value does not match {bare}", source)
    if isinstance(value, list) and origin in (list, tuple):
        for index, item in enumerate(value):
            element = args[0] if origin is list or args[-1] is Ellipsis else args[index]
            validate_value(item, element, source)
        return
    if isinstance(value, dict) and origin is dict:
        for key, item in value.items():
            TypeAdapter(args[0]).validate_python(key)
            validate_value(item, args[1], source)
        return
    if isinstance(value, dict) and isinstance(bare, type) and issubclass(bare, BaseModel):
        validate_fields(value, bare, lambda _: source)
        return
    raise ProjectError(f"Referenced value does not match {bare}", source)


def validate_fields(data, cls, location):
    fields = cls.model_fields
    known = {field.alias or name: field for name, field in fields.items()}
    if cls.model_config.get("extra") == "forbid":
        for key in data.keys() - known.keys():
            raise ProjectError(f"Unknown field '{key}' on {cls.__name__}", location((key,)))
    for key, info in known.items():
        if key not in data:
            if info.is_required():
                raise ProjectError(f"Missing required field '{key}'", location(()))
            continue
        try:
            validate_value(data[key], info.rebuild_annotation(), location((key,)))
        except (ValueError, TypeError) as error:
            if isinstance(error, ProjectError):
                raise
            raise ProjectError(str(error), location((key,))) from error


def authored_schema(cls):
    """Input JSON Schema accepts reference strings wherever a field value is allowed."""
    schema = cls.model_json_schema()
    reference = {"type": "string", "pattern": r"\$\{[^{}]+\}"}

    def transform(node, root=False):
        if not isinstance(node, dict):
            return node
        result = dict(node)
        if "properties" in result:
            result["properties"] = {
                key: (
                    transform(value)
                    if root and key in ("name", "type")
                    else {"anyOf": [transform(value), reference]}
                )
                for key, value in result["properties"].items()
            }
        if "$defs" in result:
            result["$defs"] = {key: transform(value) for key, value in result["$defs"].items()}
        for key in ("items", "additionalProperties"):
            if isinstance(result.get(key), dict):
                result[key] = {"anyOf": [transform(result[key]), reference]}
        for key in ("anyOf", "oneOf", "allOf", "prefixItems"):
            if key in result:
                result[key] = [transform(value) for value in result[key]]
        return result

    result = transform(schema, root=True)
    properties = result.setdefault("properties", {})
    properties.setdefault("type", {})["const"] = cls.type_name()
    properties["depends_on"] = {
        "type": "array",
        "items": {"type": "string", "pattern": r"^(resources|tests)\.[^.]+$"},
    }
    logger.debug("Generated authored schema for %s", cls.__name__)
    return result
