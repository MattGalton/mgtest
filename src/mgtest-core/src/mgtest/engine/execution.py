from __future__ import annotations

import logging

from mgtest.engine.plugin.plugin_registries import PluginCatalog
from mgtest.engine.project.compiler import CompiledProject, ProjectCompiler
from mgtest.engine.project.model import ProjectModel
from mgtest.engine.session import ExecutionSession

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, catalog: PluginCatalog | None = None):
        self.catalog = catalog

    def compile(self, model: ProjectModel) -> CompiledProject:
        """Compile one loaded YAML project into an immutable executable snapshot."""
        if self.catalog is None:
            raise RuntimeError("An Engine catalog is required to compile a project")
        compiled = ProjectCompiler(self.catalog).compile(model)
        logger.info(
            "Created execution plan with %d definitions and %d checks",
            len(compiled.definitions),
            len(compiled.test_order),
        )
        return compiled

    def run(self, project: CompiledProject, workspace=None) -> list[object]:
        """Execute a compiled snapshot through the sole lifecycle authority."""
        return ExecutionSession(project, workspace).run()
