import argparse
from pathlib import Path

from mgtest.engine import Engine, HydraConfigurationProvider, RunRequest, YamlConfigurationProvider
from mgtest.engine.plugin import PluginImporter

COMMAND = "run"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("path", type=Path, help="Suite or Hydra configuration directory")
    parser.add_argument("overrides", nargs="*", help="Hydra overrides")
    parser.add_argument("--hydra", action="store_true", help="Compose configuration with Hydra")
    parser.add_argument("--config-name", default="config", help="Hydra root configuration name")
    parser.set_defaults(func=run)


def run(args):
    importer = PluginImporter()
    importer.load()
    provider = HydraConfigurationProvider() if args.hydra else YamlConfigurationProvider()
    request = RunRequest(args.path, config_name=args.config_name, overrides=tuple(args.overrides))
    engine = Engine(importer.catalog)
    engine.run(engine.plan(provider, request))
    return 0
