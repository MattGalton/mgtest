"""Bounded resource cache persistence."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from mgtest.runtime.state import directory_size, read_json, runtime_path

logger = logging.getLogger(__name__)


class CacheStore:
    """Content-addressed local storage for resource inputs."""

    def __init__(self, root: Path, max_size_mb: int):
        self.root = root
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def directory(self, namespace: str, identity: str) -> Path:
        digest = hashlib.sha256(identity.encode()).hexdigest()
        entry = self.root / namespace / digest
        entry.mkdir(parents=True, exist_ok=True)
        metadata_path = entry / "metadata.json"
        metadata = read_json(metadata_path)
        metadata.update({"identity": identity, "namespace": namespace})
        metadata.setdefault("hits", 0)
        metadata.setdefault("misses", 0)
        metadata_path.write_text(json.dumps(metadata) + "\n")
        path = entry / "data"
        path.mkdir(exist_ok=True)
        path.touch()
        self.prune(exclude=entry)
        return path

    def record_result(self, path: Path, *, hit: bool) -> None:
        metadata_path = path.parent / "metadata.json"
        metadata = read_json(metadata_path)
        key = "hits" if hit else "misses"
        metadata[key] = metadata.get(key, 0) + 1
        metadata_path.write_text(json.dumps(metadata) + "\n")

    def prune(self, *, exclude: Path | None = None) -> None:
        entries = [path for path in self.root.glob("*/*") if path.is_dir()]
        total = sum(directory_size(path) for path in entries)
        for path in sorted(entries, key=lambda item: item.stat().st_mtime):
            if total <= self.max_size_bytes:
                break
            if path == exclude:
                continue
            size = directory_size(path)
            logger.debug("Pruning cache entry %s", path)
            shutil.rmtree(path, ignore_errors=True)
            total -= size


def cache_entries(root: Path) -> list[dict]:
    """Describe the cache entries retained for a project."""
    entries = []
    for path in runtime_path(root).glob("cache/*/*"):
        if not path.is_dir():
            continue
        metadata_path = path / "metadata.json"
        metadata = read_json(metadata_path) if metadata_path.is_file() else {}
        entries.append(
            {
                "namespace": path.parent.name,
                "key": path.name,
                "identity": metadata.get("identity"),
                "hits": metadata.get("hits", 0),
                "misses": metadata.get("misses", 0),
                "path": str(path),
                "size_bytes": directory_size(path),
                "last_used_at": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
            }
        )
    return sorted(entries, key=lambda entry: entry["last_used_at"], reverse=True)
