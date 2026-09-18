"""Project-local runtime paths and persisted settings."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from mgtest.project.layout import ProjectLayout

DEFAULT_CONFIG = {
    "cache": {"max_size_mb": 1024},
    "runs": {"max_count": 50, "max_age_days": 30},
}


def runtime_path(root: Path) -> Path:
    """Return the generated-state directory for a project."""
    return ProjectLayout(root.resolve()).runtime_dir


def load_settings(root: Path) -> dict:
    """Load and validate a project's runtime retention settings."""
    path = runtime_path(root) / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False))
        return DEFAULT_CONFIG
    values = yaml.safe_load(path.read_text()) or {}
    if not isinstance(values, dict):
        raise ValueError(f"Runtime configuration must be a mapping: {path}")
    cache = values.get("cache", {})
    runs = values.get("runs", {})
    size = cache.get("max_size_mb", DEFAULT_CONFIG["cache"]["max_size_mb"])
    max_count = runs.get("max_count", DEFAULT_CONFIG["runs"]["max_count"])
    max_age_days = runs.get("max_age_days", DEFAULT_CONFIG["runs"]["max_age_days"])
    if not isinstance(size, int) or size < 1:
        raise ValueError(f"cache.max_size_mb must be a positive integer: {path}")
    if not isinstance(max_count, int) or max_count < 1:
        raise ValueError(f"runs.max_count must be a positive integer: {path}")
    if not isinstance(max_age_days, int) or max_age_days < 1:
        raise ValueError(f"runs.max_age_days must be a positive integer: {path}")
    return {
        "cache": {"max_size_mb": size},
        "runs": {"max_count": max_count, "max_age_days": max_age_days},
    }


def ensure_runtime(root: Path) -> None:
    """Create and validate generated project state without starting a run."""
    load_settings(root.resolve())


def directory_size(path: Path) -> int:
    """Return the recursive byte size of a directory."""
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def read_json(path: Path) -> dict:
    """Read a JSON mapping, treating absent or malformed files as empty."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def now() -> str:
    """Return a UTC timestamp suitable for manifests."""
    return datetime.now(UTC).isoformat()
