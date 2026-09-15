"""
The entry-point for the "top-level" command line utility mgtest

Usage examples:
```
mgtest init ./
mgtest tooling --output-dir ./
mgtest --help
```
"""


def _discover_commands():
    """ "Look for mgtest_*.py files in this directory and return their imports"""
    import importlib.util
    import sys
    from pathlib import Path

    dir = Path(__file__).parent
    prefix = "mgtest_"

    modules = []

    for file in dir.glob(f"{prefix}*.py"):
        mod_name = file.stem
        spec = importlib.util.spec_from_file_location(mod_name, file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            modules.append(mod)
    return modules


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="mgtest", description="mgtest CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for module in _discover_commands():
        subparser = subparsers.add_parser(module.COMMAND, help=f"{module.COMMAND} command")
        module.populate_parser(subparser)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    from mgtest.internal.logging import setup_logging

    setup_logging()
    main()
