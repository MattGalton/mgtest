"""YAML-defined specialisations of registered mgtest definition types."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, create_model

from mgtest.api._definitions import SpecBase
from mgtest.api.resource import ResourceSpec
from mgtest.api.test import TestSpec
from mgtest.engine.plugin.plugin_registries import PluginCatalog, PluginRegistry

logger = logging.getLogger(__name__)

_SPECIALISATION_FIELD = "specialises"


def load_yaml_specialisations(path: Path, catalog: PluginCatalog, *, strict: bool = True) -> int:
    """Register the ``*.yaml`` type specialisations declared below *path*.

    A specialisation's filename is its type name.  Its ``specialises`` field names a
    previously registered type in the matching resource or test plugin directory;
    every other field becomes a default which a concrete definition may override.
    """
    registry = _registry_for(path, catalog)
    base_type = ResourceSpec if path.name == "resources" else TestSpec
    manifests = sorted(
        candidate
        for candidate in path.rglob("*.y*ml")
        if candidate.is_file() and not candidate.name.startswith("_")
    )
    pending = list(manifests)
    count = 0
    while pending:
        unresolved: list[tuple[Path, dict[str, Any]]] = []
        progressed = False
        for manifest in pending:
            try:
                data = _mapping(manifest)
                parent_name = data.get(_SPECIALISATION_FIELD)
                if not isinstance(parent_name, str) or not parent_name:
                    raise ValueError(
                        f"YAML specialisation {manifest} requires a nonempty "
                        f"'{_SPECIALISATION_FIELD}' field"
                    )
                if parent_name not in registry:
                    unresolved.append((manifest, data))
                    continue
                type_name = manifest.stem
                if type_name in registry:
                    raise ValueError(f"Type '{type_name}' already registered ({manifest})")
                parent = registry[parent_name]
                if not issubclass(parent, base_type):
                    raise ValueError(
                        f"{manifest} specialises {parent_name!r}, which is not a "
                        f"{path.name[:-1]} type"
                    )
                defaults = specialisation_defaults(manifest, data, parent)
                specialised = _specialise(type_name, parent, defaults, manifest)
                registry.register(type_name, specialised)
                logger.info("Registered YAML %s specialisation %s", path.name[:-1], type_name)
                count += 1
                progressed = True
            except (ValueError, yaml.YAMLError) as error:
                if strict:
                    raise
                logger.debug("Skipping invalid YAML specialisation %s: %s", manifest, error)
                progressed = True
        if not unresolved:
            return count
        if not progressed:
            names = ", ".join(
                f"{manifest.name} -> {data.get(_SPECIALISATION_FIELD, '<missing>')}"
                for manifest, data in unresolved
            )
            if not strict:
                logger.debug("Skipping unresolved YAML specialisations: %s", names)
                return count
            raise ValueError(f"Unknown or cyclic YAML specialisation: {names}")
        # Reconstruct the manifests rather than retaining mutated configuration.
        pending = [manifest for manifest, _ in unresolved]
    return count


def _registry_for(path: Path, catalog: PluginCatalog) -> PluginRegistry:
    if path.name == "resources":
        return catalog.resources
    if path.name == "tests":
        return catalog.tests
    raise ValueError(f"YAML specialisations must be under resources or tests: {path}")


def _mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"YAML specialisation must be a mapping: {path}")
    return dict(data)


def specialisation_parent(
    source: Path, data: dict[str, Any], registry: PluginRegistry, kind: str
) -> type:
    """Return the registered parent selected by a YAML specialisation document."""
    parent_name = data.get(_SPECIALISATION_FIELD)
    if not isinstance(parent_name, str) or not parent_name:
        raise ValueError(
            f"YAML specialisation {source} requires a nonempty '{_SPECIALISATION_FIELD}' field"
        )
    parent = registry.get(parent_name)
    if parent is None:
        raise ValueError(f"Unknown {kind[:-1]} type '{parent_name}'")
    base_type = ResourceSpec if kind == "resources" else TestSpec
    if not issubclass(parent, base_type):
        raise ValueError(f"{source} specialises {parent_name!r}, which is not a {kind[:-1]} type")
    return parent


def specialisation_defaults(
    source: Path, data: dict[str, Any], parent: type[SpecBase]
) -> dict[str, Any]:
    """Validate and return the defaults supplied by a YAML specialisation."""
    defaults = {key: value for key, value in data.items() if key != _SPECIALISATION_FIELD}
    _validate_defaults(source, defaults, parent)
    return defaults


def _validate_defaults(path: Path, defaults: dict[str, Any], parent: type[SpecBase]) -> None:
    forbidden = {"type", "name", _SPECIALISATION_FIELD} & defaults.keys()
    if forbidden:
        fields = ", ".join(sorted(forbidden))
        raise ValueError(f"YAML specialisation {path} cannot set {fields}")
    unknown = defaults.keys() - parent.model_fields.keys()
    if unknown:
        fields = ", ".join(sorted(unknown))
        raise ValueError(f"YAML specialisation {path} has unknown fields: {fields}")


def _specialise(
    type_name: str, parent: type[SpecBase], defaults: dict[str, Any], source: Path
) -> type[SpecBase]:
    fields = {
        name: (parent.model_fields[name].annotation, value) for name, value in defaults.items()
    }
    result = cast(
        type[SpecBase],
        create_model(
            type_name,
            __base__=cast(type[BaseModel], parent),
            __module__="mgtest.yaml_specialisations",
            **cast(Any, fields),
        ),
    )
    result.TYPE = type_name
    result.__doc__ = f"YAML specialisation of {parent.type_name()} declared in {source}."
    result.__mgtest_specialisation_source__ = source  # type: ignore[attr-defined]
    return result
