import argparse
import logging
from pathlib import Path

from mgtest.engine.config.project_layout import ProjectLayout

logger = logging.getLogger(__name__)

COMMAND = "init"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("./"),
        help=("Initialise an example mgtest directory here"),
    )
    parser.set_defaults(func=run)


def run(args):
    base_dir: Path = args.path.resolve()
    project = ProjectLayout.create(base_dir)
    project.validate()
    return 0


def main():
    from mgtest.internal.logging import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(prog="mgtest_init")
    populate_parser(parser)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main()
