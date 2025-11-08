"""Forward the optional language server through the main mgtest CLI."""

import argparse
import importlib
import sys

COMMAND = "lsp"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="Arguments passed to pylsp")
    parser.set_defaults(func=run)


def run(args):
    try:
        main = importlib.import_module("mgtest_lsp.server").main
    except ModuleNotFoundError as error:
        if error.name == "mgtest_lsp":
            raise SystemExit("Install mgtest-core[lsp] before running 'mgtest lsp'.") from None
        raise
    sys.argv = ["mgtest-lsp", *args.arguments]
    return main()
