"""Project and plugin lookup shared by analysis features."""

from __future__ import annotations

from pathlib import Path

import yaml

from mgtest.engine.plugin import PluginCatalog, PluginImporter
from mgtest.project.layout import ProjectLayout, project_plugin_paths
from mgtest.project.loading import load_project

from .documents import definitions


class AnalysisContext:
    """Own catalog lifetime and project-scoped definition resolution."""

    def __init__(self, root: Path | None = None, extra_paths: list[Path] | None = None):
        self.root = root.resolve() if root else None
        self.catalog = PluginCatalog()
        local_paths = extra_paths
        if local_paths is None and self.root is not None:
            local_paths = project_plugin_paths(self.root)
        PluginImporter(
            self.catalog,
            extra_paths=local_paths,
            ignore_yaml_specialisation_errors=True,
        ).load()
        self._catalogs: dict[Path, PluginCatalog] = {}

    def catalog_for(self, path: Path) -> PluginCatalog:
        root = ProjectLayout.find_root(path)
        if root is None or root == self.root:
            return self.catalog
        if root not in self._catalogs:
            catalog = PluginCatalog()
            PluginImporter(catalog, extra_paths=project_plugin_paths(root)).load()
            self._catalogs[root] = catalog
        return self._catalogs[root]

    @staticmethod
    def project_context(path: Path):
        root = ProjectLayout.find_root(path)
        if root is None:
            return None
        try:
            model = load_project(root)
        except (OSError, ValueError, yaml.YAMLError):
            return None
        suite = next((suite for suite in model.suites.values() if suite.path == path.parent), None)
        return (model, suite) if suite else None

    @staticmethod
    def visible_definitions(model, suite, kind: str, current_path: Path) -> dict[str, str]:
        current_path = current_path.resolve()
        return {
            name: identity
            for name, identity in model.visible(suite.id, kind).items()
            if model.definitions[identity].source.path.resolve() != current_path
        }

    @staticmethod
    def variable_location(model, suite, name: str):
        for node in model.ancestors(suite.id):
            if source := node.variable_locations.get((name,)):
                return source
        return None

    @staticmethod
    def project_documents(root: Path) -> dict[Path, str]:
        documents = {}
        for candidate in root.rglob("*.y*ml"):
            if not ProjectLayout.is_mgtest_document(candidate):
                continue
            try:
                documents[candidate] = candidate.read_text(encoding="utf-8")
            except OSError:
                continue
        return documents

    def project_definitions(self, path: Path) -> dict[str, dict[str, Path]]:
        """Build the lightweight index used when an unsaved document cannot load."""
        index: dict[str, dict[str, Path]] = {"resources": {}, "tests": {}}
        root = ProjectLayout.find_root(path) or self.root
        if root is None or not root.is_dir():
            return index
        layout = ProjectLayout(root)
        for candidate in root.rglob("*.y*ml"):
            kind = layout.definition_kind(candidate)
            if kind is None or not layout.is_discoverable_directory(candidate.parent):
                continue
            try:
                data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            for _, declared in definitions(candidate, data):
                for definition in declared:
                    name = definition.get("name")
                    if isinstance(name, str):
                        index[kind].setdefault(name, candidate)
        return index
