# mgtest

`mgtest` is a declarative system-test framework. YAML describes resources and
assertions, Pydantic validates definitions, and an engine manages resource lifecycle
while pytest supplies collection and reporting.

## Layout

```text
mgtest/
  builtin/resources/   # optional development plugins
  builtin/tests/
  tests/
    my_suite/
      r_service.yml
      t_service.yml
```

Run ordinary `pytest`; the installed `pytest11` entry point collects each suite.

## Plugins

Plugins are Python packages exposing spec classes through entry points:

```toml
[project.entry-points."mgtest.resources"]
container = "my_plugin:ContainerSpec"

[project.entry-points."mgtest.tests"]
http = "my_plugin:HttpSpec"
```

`MGT_PLUGIN_PATHS` and project `builtin/` directories remain available for local
development. Files there may expose spec classes or a `register(catalog)` function.

## Hydra

Install `mgtest[hydra]` and use `HydraConfigurationProvider` for configuration
composition, interpolation, overrides, and launcher integrations. The provider uses
Hydra's Compose API and produces the same execution plan as conventional YAML;
Hydra never owns pytest startup or resource lifecycle.

```python
from pathlib import Path
from mgtest.engine import Engine, HydraConfigurationProvider, RunRequest
from mgtest.engine.plugin import PluginImporter

plugins = PluginImporter()
plugins.load()
engine = Engine(plugins.catalog)
plan = engine.plan(
    HydraConfigurationProvider(),
    RunRequest(Path("conf"), overrides=("message=hello",)),
)
engine.run(plan)
```

Hydra configurations resolve to `resource`/`resources` and `test`/`tests` mappings.
mgtest deliberately retains stable `type` discriminators instead of exposing Hydra
`_target_` implementation paths.

