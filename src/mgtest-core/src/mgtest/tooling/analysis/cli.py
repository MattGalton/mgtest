"""Command-line entry point for editor-independent analysis."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from mgtest.project.layout import ProjectLayout

from .service import AnalysisService
from .types import Diagnostic


def main(argv: list[str] | None = None) -> int:
    """Analyse mgtest YAML documents for CI or editor debugging."""
    parser = argparse.ArgumentParser(prog="mgtest-analyse")
    parser.add_argument("paths", nargs="+", type=Path, help="mgtest YAML files to analyse")
    parser.add_argument("--root", type=Path, help="Project root used for project analysis")
    parser.add_argument("--json", action="store_true", help="Write diagnostics as JSON")
    args = parser.parse_args(argv)
    root = (args.root or ProjectLayout.find_root(args.paths[0]) or Path.cwd()).resolve()
    service = AnalysisService(root)
    results = []
    for path in args.paths:
        path = path.resolve()
        try:
            diagnostics = service.analyse(path, path.read_text(encoding="utf-8"))
        except OSError as error:
            diagnostics = [Diagnostic(str(error), code="io")]
        results.append({"path": str(path), "diagnostics": [asdict(item) for item in diagnostics]})
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            for issue in result["diagnostics"]:
                print(
                    f"{result['path']}:{issue['line'] + 1}:{issue['character'] + 1}: "
                    f"{issue['code']}: {issue['message']}"
                )
    return 1 if any(result["diagnostics"] for result in results) else 0
