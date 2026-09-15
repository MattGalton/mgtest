import os
from pathlib import Path

from mgtest.env import MGT_HOME


class Home:
    """
    Centralized mgtest home.
    Holds schemas, downloaded tests/resources, and cache.
    """

    def __init__(self, base: Path = None):
        if base is not None:
            self.base = base
        else:
            self.base = Path(os.environ.get(MGT_HOME, self.default_base()))
        self.schemas_dir = self.base / "schemas"
        self.resources_dir = self.base / "resources"
        self.tests_dir = self.base / "tests"

    def ensure_exists(self) -> "Home":
        """Create the home directory structure explicitly."""
        for directory in (self.schemas_dir, self.resources_dir, self.tests_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return self

    @staticmethod
    def default_base() -> Path:
        return (Path.home() / ".mgtest").expanduser().resolve()
