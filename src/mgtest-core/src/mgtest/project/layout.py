"""Filesystem convention for an mgtest project."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)
YAML_SUFFIXES = frozenset({".yaml", ".yml"})
VARIABLE_FILENAMES = frozenset({"vars.yaml", "vars.yml"})
RESOURCE_PREFIX = "r_"
TEST_PREFIX = "t_"
SUITE_PREFIX = "s_"
RUNTIME_DIRECTORY = ".mgtest"
BUILTIN_DIRECTORY = "builtin"
RESOURCE_GLOBS = ("**/r_*.yml", "**/r_*.yaml")
TEST_GLOBS = ("**/t_*.yml", "**/t_*.yaml")


class InvalidProjectError(RuntimeError):
    pass


def project_plugin_paths(root: Path) -> list[Path]:
    """Return existing project-local development plugin directories."""
    builtin = root.resolve() / BUILTIN_DIRECTORY
    paths = [path for kind in ("resources", "tests") if (path := builtin / kind).is_dir()]
    logger.info("Found project plugin paths: %s", paths)
    return paths


@dataclass(frozen=True)
class ProjectLayout:
    root: Path

    @property
    def runtime_dir(self) -> Path:
        """Directory holding generated per-project state."""
        return self.root / RUNTIME_DIRECTORY

    @property
    def config_path(self) -> Path:
        return self.runtime_dir / "config.yaml"

    @property
    def variables_path(self) -> Path:
        return self.root / "vars.yaml"

    @property
    def plugins_dir(self) -> Path:
        return self.root / BUILTIN_DIRECTORY

    @staticmethod
    def is_mgtest_resource(path: Path) -> bool:
        """Whether *path* is a resource definition document."""
        return path.suffix in YAML_SUFFIXES and path.name.startswith(RESOURCE_PREFIX)

    @staticmethod
    def is_mgtest_test(path: Path) -> bool:
        """Whether *path* is a test definition document."""
        return path.suffix in YAML_SUFFIXES and path.name.startswith(TEST_PREFIX)

    @staticmethod
    def is_mgtest_suite(path: Path) -> bool:
        """Whether *path* is an explicitly declared suite directory."""
        return path.is_dir() and path.name.startswith(SUITE_PREFIX)

    @staticmethod
    def is_mgtest_suite_document(path: Path) -> bool:
        """Whether *path* is a suite manifest that groups existing checks."""
        return path.suffix in YAML_SUFFIXES and path.name.startswith(SUITE_PREFIX)

    @staticmethod
    def yaml_specialisation_kind(path: Path) -> str | None:
        """Return the kind of a YAML type declaration below ``builtin``.

        Definitions may be grouped in subdirectories, so the directory immediately
        below ``builtin`` determines whether the declaration derives a resource or
        a test type.
        """
        if path.suffix not in YAML_SUFFIXES:
            return None
        parts = path.parts
        for index, part in enumerate(parts[:-1]):
            if part != BUILTIN_DIRECTORY or index + 1 >= len(parts):
                continue
            kind = parts[index + 1]
            if kind in {"resources", "tests"}:
                return kind
        return None

    @classmethod
    def definition_kind(cls, path: Path) -> str | None:
        """Return the definition collection for a document, if it is an mgtest document."""
        if cls.is_mgtest_resource(path):
            return "resources"
        if cls.is_mgtest_test(path):
            return "tests"
        return None

    @staticmethod
    def is_variables_document(path: Path) -> bool:
        """Whether *path* supplies suite variables."""
        return path.name in VARIABLE_FILENAMES

    @classmethod
    def is_mgtest_document(cls, path: Path) -> bool:
        """Whether *path* follows any supported mgtest YAML convention."""
        return (
            cls.is_variables_document(path)
            or cls.definition_kind(path) is not None
            or cls.is_mgtest_suite_document(path)
            or cls.yaml_specialisation_kind(path) is not None
        )

    def is_discoverable_directory(self, path: Path) -> bool:
        """Whether recursive loading should enter *path*."""
        try:
            relative_parts = path.resolve().relative_to(self.root.resolve()).parts
        except ValueError:
            return False
        if not path.is_dir() or any(
            part in {self.plugins_dir.name, self.runtime_dir.name} for part in relative_parts
        ):
            return False
        return path.resolve() == self.root.resolve() or self.is_mgtest_suite(path)

    @classmethod
    def find_root(cls, path: Path) -> Path | None:
        """Find the nearest project root from a directory or file inside a project."""
        path = path.resolve()
        if path.is_file():
            path = path.parent
        for candidate in (path, path / "mgtest", *path.parents):
            layout = cls(candidate)
            if candidate.is_dir() and (layout.plugins_dir.is_dir() or layout.runtime_dir.is_dir()):
                return candidate
        return None

    @classmethod
    def create(cls, root: Path) -> "ProjectLayout":
        project = cls(root.resolve())
        for path in (
            project.root / "resources",
            project.root / "tests",
            project.plugins_dir / "resources",
            project.plugins_dir / "tests",
        ):
            path.mkdir(parents=True, exist_ok=True)
        # Imported here to keep the filesystem convention independent of runtime services.
        from mgtest.runtime.state import ensure_runtime

        ensure_runtime(project.root)
        logger.debug("Created project layout at %s", project.root)
        return project

    @staticmethod
    def exists(root: Path) -> bool:
        root = root.resolve()
        return root.is_dir() and (root / "tests").is_dir()

    def validate(self) -> None:
        if not self.exists(self.root):
            raise InvalidProjectError(f"Project configuration not found in {self.root}")
