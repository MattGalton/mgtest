import json
import sys

import pytest

from mgtest.engine import Engine, HydraConfigurationProvider, RunRequest
from mgtest.engine.plugin import PluginImporter


def test_hydra_composes_into_the_normal_execution_plan(tmp_path):
    pytest.importorskip("hydra")
    (tmp_path / "config.yaml").write_text(
        json.dumps(
            {
                "python_path": sys.executable,
                "resource": {
                    "type": "Executable",
                    "name": "python",
                    "path": "${python_path}",
                    "args": ["-u", "-c", "print('from hydra')"],
                },
                "test": {
                    "type": "StreamRegex",
                    "name": "output",
                    "resource": "python",
                    "pattern": "${message}",
                },
                "message": "hydra",
            }
        )
    )
    importer = PluginImporter()
    importer.load()
    engine = Engine(importer.catalog)
    plan = engine.plan(HydraConfigurationProvider(), RunRequest(tmp_path))
    assert engine.run(plan)[0].found is True
