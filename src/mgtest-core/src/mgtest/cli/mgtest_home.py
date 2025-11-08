import argparse
import json
import logging
from pathlib import Path

from mgtest.runtime.cache import cache_entries
from mgtest.runtime.maintenance import (
    clear_runtime,
    doctor,
    ensure_runtime,
    list_runs,
    prune_runtime,
    run_details,
    runtime_status,
)

COMMAND = "home"
logger = logging.getLogger(__name__)


def populate_parser(parser: argparse.ArgumentParser):
    parser.add_argument("path", type=Path, nargs="?", default=Path("."), help="mgtest project")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--clear",
        action="store_true",
        help="Remove this project's cached resources and saved run artifacts",
    )
    actions.add_argument("--clear-cache", action="store_true", help="Remove cached resources")
    actions.add_argument("--clear-runs", action="store_true", help="Remove saved run artifacts")
    actions.add_argument(
        "--prune", action="store_true", help="Apply cache and run retention limits"
    )
    actions.add_argument("--runs", action="store_true", help="List saved runs")
    actions.add_argument("--cache", action="store_true", help="List cache entries")
    actions.add_argument(
        "--show-run", metavar="RUN_ID", help="Show one run's manifest and config path"
    )
    actions.add_argument("--doctor", action="store_true", help="Check local tool availability")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.set_defaults(func=run)


def run(args):
    root = args.path.resolve()
    logger.debug("Inspecting runtime state for %s", root)
    if args.clear:
        state = clear_runtime(root)
        result = {"cleared": [str(state / "cache"), str(state / "runs")]}
    elif args.clear_cache:
        state = clear_runtime(root, runs=False)
        result = {"cleared": [str(state / "cache")]}
    elif args.clear_runs:
        state = clear_runtime(root, cache=False)
        result = {"cleared": [str(state / "runs")]}
    elif args.prune:
        result = prune_runtime(root)
    elif args.runs:
        result = list_runs(root)
    elif args.cache:
        result = cache_entries(root)
    elif args.show_run:
        result = run_details(root, args.show_run)
    elif args.doctor:
        result = doctor(root)
    else:
        ensure_runtime(root)
        result = runtime_status(root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print(result)
    return 0


def _print(result):
    if isinstance(result, list):
        for item in result:
            print("  ".join(f"{key}={value}" for key, value in item.items()))
        return
    if "project" in result:
        cache = result["cache"]
        runs = result["runs"]
        print(f"Project: {result['project']}")
        print(f"Runtime: {result['runtime']}")
        print(
            f"Cache: {_size(cache['size_bytes'])} / {cache['max_size_mb']} MiB "
            f"({cache['entries']} entries)"
        )
        attempts = cache["hits"] + cache["misses"]
        if attempts:
            print(
                f"Cache results: {cache['hits']} hits, {cache['misses']} misses "
                f"({cache['hits'] / attempts:.0%} hit rate)"
            )
        print(f"Runs: {runs['count']} retained, {runs['failed']} failed")
        if runs["latest"]:
            latest = runs["latest"]
            print(f"Latest run: {latest['id']} ({latest['status']})")
        print(f"Config: {result['config']}")
        return
    print(json.dumps(result, indent=2))


def _size(value: int) -> str:
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value / 1024 / 1024:.1f} MiB"


def main():
    from mgtest.logging import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(prog="mgtest_home")
    populate_parser(parser)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main()
