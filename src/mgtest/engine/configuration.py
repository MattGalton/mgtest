from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from mgtest.engine.config.resource_file import ResourceFile
from mgtest.engine.config.test_file import TestFile


@dataclass(frozen=True)
class RawConfiguration:
    resources: tuple[Mapping[str, Any], ...] = ()
    tests: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class RunRequest:
    config_dir: Path
    config_name: str = "config"
    overrides: tuple[str, ...] = ()


class ConfigurationProvider(Protocol):
    def compose(self, request: RunRequest) -> RawConfiguration: ...


class YamlConfigurationProvider:
    """Load the existing r_*.yml and t_*.yml suite convention."""

    def compose(self, request: RunRequest) -> RawConfiguration:
        resources: list[Mapping[str, Any]] = []
        tests: list[Mapping[str, Any]] = []
        for path in sorted(request.config_dir.glob("r_*.y*ml")):
            data = self._load(path)
            resources.extend(ResourceFile.from_yaml_dict(data).resources)
        for path in sorted(request.config_dir.glob("t_*.y*ml")):
            data = self._load(path)
            tests.extend(TestFile.from_yaml_dict(data).tests)
        return RawConfiguration(tuple(resources), tuple(tests))

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        return data
