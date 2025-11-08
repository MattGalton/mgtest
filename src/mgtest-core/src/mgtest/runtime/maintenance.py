"""Inspection and retention operations for generated project state."""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mgtest.runtime.cache import CacheStore, cache_entries
from mgtest.runtime.state import (
    directory_size,
    ensure_runtime,
    load_settings,
    read_json,
    runtime_path,
)

logger = logging.getLogger(__name__)


def clear_runtime(root: Path, *, cache: bool = True, runs: bool = True) -> Path:
    """Clear generated cache and run artifacts while preserving settings."""
    root = root.resolve()
    ensure_runtime(root)
    state = runtime_path(root)
    for name, selected in (("cache", cache), ("runs", runs)):
        if selected:
            shutil.rmtree(state / name, ignore_errors=True)
    return state


def list_runs(root: Path) -> list[dict]:
    """Return retained run manifests, newest first."""
    runs = []
    for path in runtime_path(root).glob("runs/*"):
        manifest = read_json(path / "manifest.json")
        if manifest:
            runs.append(
                {
                    "id": path.name,
                    "status": manifest.get("status", "unknown"),
                    "started_at": manifest.get("started_at"),
                    "finished_at": manifest.get("finished_at"),
                    "size_bytes": directory_size(path),
                    "path": str(path),
                }
            )
    return sorted(runs, key=lambda run: run["started_at"] or "", reverse=True)


def run_details(root: Path, run_id: str) -> dict:
    """Return one saved run's manifest and artifact locations."""
    path = runtime_path(root) / "runs" / run_id
    manifest = read_json(path / "manifest.json")
    if not manifest:
        raise ValueError(f"Unknown run '{run_id}' in {runtime_path(root) / 'runs'}")
    return {
        "path": str(path),
        "manifest": manifest,
        "resolved_config": str(path / "resolved-config.yaml"),
    }


def prune_runtime(root: Path) -> dict[str, int]:
    """Apply cache size and run retention limits."""
    root = root.resolve()
    settings = load_settings(root)
    state = runtime_path(root)
    CacheStore(state / "cache", settings["cache"]["max_size_mb"]).prune()
    removed = 0
    cutoff = datetime.now(UTC).timestamp() - settings["runs"]["max_age_days"] * 86400
    for index, run in enumerate(list_runs(root)):
        expired = Path(run["path"]).stat().st_mtime < cutoff
        exceeds_count = index >= settings["runs"]["max_count"]
        if run["status"] != "running" and (expired or exceeds_count):
            shutil.rmtree(run["path"], ignore_errors=True)
            removed += 1
    return {"runs_removed": removed}


def runtime_status(root: Path) -> dict[str, Any]:
    """Return summary information for a project's generated state."""
    root = root.resolve()
    settings = load_settings(root)
    state = runtime_path(root)
    entries = cache_entries(root)
    runs = list_runs(root)
    return {
        "project": str(root),
        "runtime": str(state),
        "config": str(state / "config.yaml"),
        "cache": {
            "path": str(state / "cache"),
            "size_bytes": directory_size(state / "cache"),
            "max_size_mb": settings["cache"]["max_size_mb"],
            "entries": len(entries),
            "hits": sum(entry["hits"] for entry in entries),
            "misses": sum(entry["misses"] for entry in entries),
        },
        "runs": {
            "path": str(state / "runs"),
            "count": len(runs),
            "failed": sum(run.get("status") == "failed" for run in runs),
            "latest": runs[0] if runs else None,
            "max_count": settings["runs"]["max_count"],
            "max_age_days": settings["runs"]["max_age_days"],
        },
    }


def doctor(root: Path) -> dict[str, Any]:
    """Check generated state and optional external command availability."""
    ensure_runtime(root)
    tools = {}
    commands = {
        "git": ["git", "--version"],
        "docker": ["docker", "--version"],
        "docker_compose": ["docker", "compose", "version"],
        "ffmpeg": ["ffmpeg", "-version"],
    }
    for name, command in commands.items():
        try:
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            tools[name] = {"available": result.returncode == 0, "version": result.stdout.strip()}
        except FileNotFoundError:
            tools[name] = {"available": False, "version": None}
    state = runtime_path(root)
    probe = state / ".write-probe"
    try:
        probe.write_text("")
        probe.unlink()
        writable = True
    except OSError:
        writable = False
    return {"runtime": str(state), "writable": writable, "tools": tools}
