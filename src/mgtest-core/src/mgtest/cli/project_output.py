"""Shared compiled-project output for CLI inspection commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mgtest.engine.project.compiler import CompiledResource


def plan_data(compiled) -> dict:
    definitions = []
    for key, node in compiled.definitions.items():
        definitions.append(
            {
                "id": key,
                "kind": "resource" if isinstance(node, CompiledResource) else "test",
                "name": node.definition.name,
                "type": node.definition.data["type"],
                "suite": node.definition.suite,
                "depends_on": sorted(compiled.graph.dependencies[key]),
            }
        )
    return {
        "root": str(compiled.model.root),
        "test_order": list(compiled.test_order),
        "definitions": definitions,
    }


def graph_dot(compiled) -> str:
    lines = ["digraph mgtest {", "  rankdir=LR;"]
    for key, node in compiled.definitions.items():
        shape = "box" if isinstance(node, CompiledResource) else "ellipse"
        label = f'{node.definition.name}\\n{node.definition.data["type"]}'
        lines.append(f'  "{key}" [label="{label}", shape={shape}];')
    for dependent, prerequisites in compiled.graph.dependencies.items():
        for prerequisite in sorted(prerequisites):
            lines.append(f'  "{prerequisite}" -> "{dependent}";')
    return "\n".join([*lines, "}"]) + "\n"


def graph_mermaid(compiled) -> str:
    names = {key: f"n{index}" for index, key in enumerate(compiled.definitions)}
    lines = ["flowchart LR"]
    for key, node in compiled.definitions.items():
        bracket = ("[", "]") if isinstance(node, CompiledResource) else ("(", ")")
        lines.append(f'{names[key]}{bracket[0]}"{node.definition.name}<br/>{node.definition.data["type"]}"{bracket[1]}')
    for dependent, prerequisites in compiled.graph.dependencies.items():
        for prerequisite in sorted(prerequisites):
            lines.append(f"{names[prerequisite]} --> {names[dependent]}")
    return "\n".join(lines) + "\n"


def render_graph(source: str, format: str) -> bytes:
    result = subprocess.run(
        ["dot", f"-T{format}"], input=source.encode(), capture_output=True, check=True
    )
    return result.stdout


def write_output(content: str | bytes, output: Path | None) -> None:
    if output is None:
        if isinstance(content, bytes):
            raise ValueError("PNG and SVG output require --output")
        print(content, end="")
    elif isinstance(content, bytes):
        output.write_bytes(content)
    else:
        output.write_text(content)


def json_plan(compiled) -> str:
    return json.dumps(plan_data(compiled), indent=2) + "\n"
