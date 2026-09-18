import logging
from pathlib import Path

from mgtest.project.loading import load_project

COMMAND = "list"
logger = logging.getLogger(__name__)


def populate_parser(parser):
    parser.add_argument("path", type=Path, help="mgtest project directory")
    parser.set_defaults(func=run)


def run(args):
    project = load_project(args.path)
    logger.info("Listing suites and checks in %s", project.root)
    print(format_project(project))
    return 0


def format_project(project):
    lines = []

    def visit(suite_id, depth):
        suite = project.suites[suite_id]
        label = "." if suite_id == "." else suite.path.name
        lines.append(f"{'  ' * depth}{label}")
        for identity in sorted(suite.tests.values()):
            lines.append(f"{'  ' * (depth + 1)}test {project.definitions[identity].name}")
        for child_id in sorted(suite.children):
            visit(child_id, depth + 1)

    visit(".", 0)
    return "\n".join(lines)
