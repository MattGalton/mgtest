from __future__ import annotations

from pathlib import Path

import pytest

from mgtest.engine.config.project_layout import ProjectLayout
from mgtest.engine.configuration import RunRequest, YamlConfigurationProvider
from mgtest.engine.execution import Engine
from mgtest.engine.plugin import PluginImporter


class MgtestProject(pytest.Directory):
    def collect(self):
        project = ProjectLayout(Path(str(self.path)))
        plugin_paths = [path for path in project.layout.plugins_subdirs if path.is_dir()]
        for suite_dir in sorted(path for path in project.tests_dir.iterdir() if path.is_dir()):
            yield MgtestSuite.from_parent(
                self, name=suite_dir.name, suite_dir=suite_dir, plugin_paths=plugin_paths
            )


class MgtestSuite(pytest.Item):
    def __init__(self, *, suite_dir: Path, plugin_paths: list[Path], **kwargs):
        super().__init__(**kwargs)
        self.suite_dir = suite_dir
        self.plugin_paths = plugin_paths

    def runtest(self):
        importer = PluginImporter(extra_paths=self.plugin_paths)
        importer.load()
        engine = Engine(importer.catalog)
        plan = engine.plan(YamlConfigurationProvider(), RunRequest(self.suite_dir))
        engine.run(plan)

    def reportinfo(self):
        return self.suite_dir, 0, f"mgtest suite: {self.name}"


def pytest_collect_directory(parent, path):
    candidate = Path(str(path))
    if (
        candidate.name == "mgtest"
        and not (candidate / "pyproject.toml").exists()
        and ProjectLayout.exists(candidate)
    ):
        return MgtestProject.from_parent(parent, path=path)
    return None
