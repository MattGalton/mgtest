import argparse
from pathlib import Path

from mgtest.cli.project_output import json_plan, write_output
from mgtest.engine.bootstrap import compile_project

COMMAND = "plan"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.set_defaults(func=run)


def run(args):
    write_output(json_plan(compile_project(args.path)), args.output)
