"""Filesystem convention for the user-wide mgtest home directory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mgtest.env import MGT_HOME

HOME_DIRECTORY = ".mgtest"


@dataclass(frozen=True)
class HomeLayout:
    """Locations for globally installed schemas and reusable definitions."""

    base: Path

    @property
    def schemas_dir(self) -> Path:
        return self.base / "schemas"

    @property
    def resources_dir(self) -> Path:
        return self.base / "resources"

    @property
    def tests_dir(self) -> Path:
        return self.base / "tests"

    @property
    def directories(self) -> tuple[Path, Path, Path]:
        """Directories created when the home layout is initialized."""
        return self.schemas_dir, self.resources_dir, self.tests_dir

    @classmethod
    def from_environment(cls) -> HomeLayout:
        """Build the layout using ``MGT_HOME`` when it is configured."""
        return cls(Path(os.environ.get(MGT_HOME, cls.default_base())).expanduser().resolve())

    @staticmethod
    def default_base() -> Path:
        """Return the standard user-wide mgtest home path."""
        return (Path.home() / HOME_DIRECTORY).expanduser().resolve()

    def ensure_exists(self) -> HomeLayout:
        """Create the global home directories."""
        for directory in self.directories:
            directory.mkdir(parents=True, exist_ok=True)
        return self
