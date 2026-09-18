import argparse
import logging
from pathlib import Path

from mgtest.engine import Engine
from mgtest.engine.bootstrap import compile_project
from mgtest.runtime import RunWorkspace

COMMAND = "run"
logger = logging.getLogger(__name__)


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("path", type=Path, help="mgtest project directory")
    parser.add_argument(
        "selector",
        nargs="?",
        help="Suite path, check name, or suite/path/check",
    )
    parser.set_defaults(func=run)


def run(args):
    logger.info("Running project %s", args.path)
    compiled = compile_project(args.path, args.selector)
    workspace = RunWorkspace.create(compiled.model.root, compiled)
    try:
        Engine().run(compiled, workspace)
    except BaseException as error:
        workspace.finalize(error)
        logger.error("Run failed; artifacts are in %s (%s)", workspace.path, error)
        raise
    workspace.finalize()
    logger.info("Run passed; artifacts are in %s", workspace.path)
    return 0
