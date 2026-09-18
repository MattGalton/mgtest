import argparse
import logging
from pathlib import Path

from mgtest.engine.plugin import PluginImporter
from mgtest.home.layout import HomeLayout
from mgtest.tooling import SchemaGenerator, write_vscode_settings
from mgtest.tooling.schema.jetbrains import write_jetbrains_schemas

COMMAND = "tooling"
logger = logging.getLogger(__name__)


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument(
        "plugin_paths",
        type=Path,
        nargs="*",
        default=[],
        help=(
            "Development plugin directories to include. By default, load only built-ins, "
            "installed entry points, and MGT_PLUGIN_PATHS."
        ),
    )
    parser.add_argument(
        "--vscode",
        type=Path,
        default=None,
        help=(
            "Path to the .vscode folder where schemas should be copied for VS Code integration. "
            "Schemas from your mgtest home will be copied here."
        ),
    )
    parser.add_argument(
        "--jetbrains",
        type=Path,
        default=None,
        help=(
            "Path to the JetBrains IDE configuration folder. "
            "Generated schemas will be copied here for IDE integration."
        ),
    )
    parser.add_argument(
        "--output-dir",
        "--output_dir",
        dest="output_dir",
        type=Path,
        default=HomeLayout.from_environment().schemas_dir,
        help="Where to write the schemas",
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    # Load and register all resources/tests
    logger.info("Generating editor tooling in %s", args.output_dir)
    loader = PluginImporter(extra_paths=args.plugin_paths)
    loader.load()

    generator = SchemaGenerator(args.output_dir, loader.catalog)
    generator.generate()

    if args.vscode:
        write_vscode_settings(generator.output_dir, args.vscode)

    if args.jetbrains:
        write_jetbrains_schemas(generator.output_dir, args.jetbrains)

    logger.info("Generated editor tooling in %s", generator.output_dir)
    return 0


def main():
    from mgtest.logging import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(prog="mgtest_schema")
    populate_parser(parser)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main()
