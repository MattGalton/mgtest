import argparse
from pathlib import Path

from mgtest.engine.plugin import PluginImporter
from mgtest.home.home import Home
from mgtest.tooling import SchemaGenerator, write_vscode_settings
from mgtest.tooling.schema.jetbrains import write_jetbrains_schemas

COMMAND = "tooling"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument(
        "plugin_paths",
        type=Path,
        nargs="*",
        default=[Path("./")],
        help=(
            "One or more paths to mgtest builtin to include when generating schemas. "
            "Schemas for tests/resources from these builtin will be generated."
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
            "Path to the JetBrains IDE configuration folder where schemas should be copied for IDE integration. "
            "Schemas from your mgtest home will be copied here."
        ),
    )
    parser.add_argument(
        "--output_dir", type=Path, default=Home().schemas_dir, help=("Where to write the schemas")
    )
    parser.set_defaults(func=run)
    return parser


def run(args):
    # Load and register all resources/tests
    loader = PluginImporter(extra_paths=args.plugin_paths)
    loader.load()

    generator = SchemaGenerator(args.output_dir, loader.catalog)
    generator.generate()

    if args.vscode:
        write_vscode_settings(generator.output_dir, args.vscode)

    if args.jetbrains:
        write_jetbrains_schemas(generator.output_dir, args.jetbrains)

    return 0


def main():
    from mgtest.internal.logging import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(prog="mgtest_schema")
    populate_parser(parser)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
