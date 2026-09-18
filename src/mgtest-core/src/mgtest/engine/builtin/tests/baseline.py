"""Path handling shared by checks that compare output with checked-in data."""

from pathlib import Path


def baseline_path(baseline: Path, source_path: Path) -> Path:
    """Resolve a baseline path relative to its owning YAML document."""
    return (
        baseline
        if baseline.is_absolute()
        else source_path.parent / baseline
    )
