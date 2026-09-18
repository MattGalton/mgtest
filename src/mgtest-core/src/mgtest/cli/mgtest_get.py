"""Collect a check's resource environment for local inspection or reproduction."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from mgtest.engine import ExecutionSession
from mgtest.engine.bootstrap import compile_project, project_root
from mgtest.runtime import GetWorkspace

COMMAND = "get"


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument(
        "target",
        help="Check selector, or project directory when a second selector is supplied",
    )
    parser.add_argument("selector", nargs="?", help="Check selector when PROJECT is supplied")
    parser.add_argument(
        "--project", type=Path, help="Project directory; defaults to enclosing project"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--prepare", action="store_true", help="Only materialise durable inputs (default)"
    )
    mode.add_argument(
        "--shell", action="store_true", help="Start resources and open an interactive shell"
    )
    mode.add_argument("--command", help="Start resources and run this shell command")
    parser.add_argument(
        "--with-prerequisites",
        action="store_true",
        help="Run prerequisite checks when their outputs are required",
    )
    parser.set_defaults(func=run)


def run(args):
    root, selector = _arguments(args)
    compiled = compile_project(root, selector)
    root = compiled.model.root
    if len(compiled.test_order) != 1:
        raise ValueError("mgtest get requires one check selector, not a suite")
    target = compiled.test_order[0]
    workspace = GetWorkspace.create(root, compiled)
    session = ExecutionSession(compiled, workspace)
    start = bool(args.shell or args.command)
    try:
        resources, prerequisites = session.collect(
            target, start=start, with_prerequisites=args.with_prerequisites
        )
        workspace.describe_get(target, resources, prerequisites)
        environment = _environment(session, workspace)
        workspace.record_environment(environment)
        print(f"Collected resources in {workspace.path}")
        if args.command:
            return subprocess.run(args.command, shell=True, env=environment, check=False).returncode
        if args.shell:
            return subprocess.run([os.environ.get("SHELL", "/bin/sh")], env=environment).returncode
        return 0
    except BaseException as error:
        workspace.finalize(error)
        raise
    finally:
        session.teardown()
        workspace.finalize()


def _arguments(args) -> tuple[Path, str]:
    if args.project:
        if args.selector:
            raise ValueError("Use either --project SELECTOR or PROJECT SELECTOR")
        return args.project.resolve(), args.target
    if args.selector:
        return Path(args.target).resolve(), args.selector
    return _project_root(Path.cwd()), args.target


def _project_root(path: Path) -> Path:
    try:
        return project_root(path)
    except ValueError as error:
        raise ValueError("Could not find an enclosing mgtest project; pass --project") from error


def _environment(session, workspace) -> dict[str, str]:
    environment = dict(os.environ)
    environment["MGTEST_GET_DIR"] = str(workspace.path)
    for identity, instance in session.instances.items():
        outputs = instance.outputs
        values = outputs.model_dump() if hasattr(outputs, "model_dump") else outputs
        if not isinstance(values, dict):
            continue
        prefix = "MGTEST_RESOURCE_" + identity.replace("::resources.", "_").upper()
        for key, value in values.items():
            if isinstance(value, (str, int, float, bool)):
                environment[f"{prefix}_{key.upper()}"] = str(value)
    return environment
