import argparse
from pathlib import Path

from mgtest.cli.project_output import (
    graph_dot,
    graph_mermaid,
    render_graph,
    write_output,
)
from mgtest.engine.bootstrap import compile_project

COMMAND = "graph"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("path", type=Path)
    parser.add_argument("--format", choices=("dot", "mermaid", "svg", "png"), default="dot")
    parser.add_argument("--output", type=Path)
    parser.set_defaults(func=run)


def run(args):
    compiled = compile_project(args.path)
    if args.format == "mermaid":
        write_output(graph_mermaid(compiled), args.output)
    else:
        dot = graph_dot(compiled)
        write_output(dot if args.format == "dot" else render_graph(dot, args.format), args.output)
