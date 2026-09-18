"""Analyse YAML through the core static-analysis implementation."""

import argparse
from pathlib import Path

COMMAND = "analyse"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("paths", nargs="+", type=Path, help="mgtest YAML files to analyse")
    parser.add_argument("--root", type=Path, help="Project root used for cross-file references")
    parser.add_argument("--json", action="store_true", help="Write diagnostics as JSON")
    parser.set_defaults(func=run)


def run(args):
    from mgtest.tooling.analysis import main

    forwarded = ["--root", str(args.root)] if args.root else []
    if args.json:
        forwarded.append("--json")
    forwarded.extend(str(path) for path in args.paths)
    return main(forwarded)
