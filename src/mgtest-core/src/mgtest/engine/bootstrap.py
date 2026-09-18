"""Shared loading and compilation entry points for mgtest front ends."""

from __future__ import annotations

from pathlib import Path

from mgtest.engine.execution import Engine
from mgtest.engine.plugin import PluginImporter
from mgtest.engine.project.compiler import CompiledProject
from mgtest.project.layout import ProjectLayout, project_plugin_paths
from mgtest.project.loading import load_project
from mgtest.project.selection import select


def project_root(path: Path) -> Path:
    """Return the mgtest root enclosing *path*."""
    if root := ProjectLayout.find_root(path):
        return root
    raise ValueError(f"Could not find an mgtest project below or above {path}")


def compile_project(path: Path, selector: str | None = None) -> CompiledProject:
    """Load plugins and compile an optionally selected project snapshot."""
    root = project_root(path)
    importer = PluginImporter(extra_paths=project_plugin_paths(root))
    importer.load()
    model = load_project(root)
    select(model, selector)
    return Engine(importer.catalog).compile(model)
