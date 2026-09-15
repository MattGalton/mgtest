from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mgtest.engine.configuration import RawConfiguration, RunRequest


class HydraConfigurationProvider:
    """Optional Hydra-backed composition without handing Hydra process control."""

    def compose(self, request: RunRequest) -> RawConfiguration:
        try:
            from hydra import compose, initialize_config_dir
            from omegaconf import OmegaConf
        except ImportError as error:
            raise RuntimeError("Install mgtest[hydra] to use HydraConfigurationProvider") from error

        with initialize_config_dir(version_base=None, config_dir=str(request.config_dir.resolve())):
            config = compose(config_name=request.config_name, overrides=list(request.overrides))
        data = OmegaConf.to_container(config, resolve=True)
        if not isinstance(data, Mapping):
            raise ValueError("Hydra's root configuration must be a mapping")
        return RawConfiguration(
            resources=tuple(self._definitions(data, "resource", "resources")),
            tests=tuple(self._definitions(data, "test", "tests")),
        )

    @staticmethod
    def _definitions(
        data: Mapping[str, Any], singular: str, plural: str
    ) -> list[Mapping[str, Any]]:
        value = data.get(plural, data.get(singular, []))
        if isinstance(value, Mapping):
            return [value]
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if not all(isinstance(item, Mapping) for item in value):
                raise ValueError(f"Hydra '{plural}' must contain mappings")
            return list(value)
        raise ValueError(f"Hydra '{plural}' must be a mapping or sequence of mappings")
