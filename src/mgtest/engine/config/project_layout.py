from dataclasses import dataclass
from pathlib import Path


class InvalidProjectError(RuntimeError):
    pass


@dataclass(frozen=True)
class _ProjectLayout:
    """
    The layout of an mgtest project is expected to be
    .
    └── mgtest
        ├── builtin
        │   ├── resources
        │   └── tests
        └── test
    """

    parent: Path
    mgtest: Path
    tests: Path
    plugins: Path
    plugins_tests: Path
    plugins_resources: Path

    def __iter__(self):
        return iter(
            [self.mgtest, self.tests, self.plugins, self.plugins_tests, self.plugins_resources]
        )

    @classmethod
    def from_root(cls, mgtest: Path):
        """parameter mgtest is the /path/to/mgtest"""
        mgtest = mgtest.resolve()
        parent = mgtest.parent

        tests = mgtest / "tests"
        plugins = mgtest / "builtin"
        plugins_tests = plugins / "tests"
        plugins_resources = plugins / "resources"
        return cls(parent, mgtest, tests, plugins, plugins_tests, plugins_resources)

    @property
    def required(self):
        """The subdirectories required for a folder to be considered an mgtest project"""
        return self.mgtest, self.tests

    @property
    def plugins_subdirs(self):
        return self.plugins_tests, self.plugins_resources


class ProjectLayout:
    """
    Represents an mgtest test project on disk.
    """

    def __init__(self, root: Path):
        self.layout = _ProjectLayout.from_root(root)

    @classmethod
    def create(cls, root: Path) -> "ProjectLayout":
        """Create a project. Does not overwrite existing an existing project"""
        project = cls(root)
        for d in project.layout:
            d.mkdir(parents=True, exist_ok=True)
        return project

    @staticmethod
    def exists(root: Path) -> bool:
        """Is there already an mgtest project here?"""
        layout = _ProjectLayout.from_root(root)
        return all(d.exists() for d in layout.required)

    @property
    def mgtest_dir(self) -> Path:
        return self.layout.mgtest

    @property
    def tests_dir(self) -> Path:
        return self.layout.tests

    @property
    def plugins_dir(self) -> Path:
        return self.layout.plugins

    @property
    def plugins_tests_dir(self) -> Path:
        return self.layout.plugins_tests

    @property
    def plugins_resources_dir(self) -> Path:
        return self.layout.plugins_resources

    def validate(self) -> None:
        if not all(p.exists() for p in self.layout.required):
            raise InvalidProjectError(
                f"At least one of the following required directories \"{';'.join(str(p) for p in self.layout.required)}\" is missing."
            )

    def has_plugins(self) -> bool:
        return self.layout.plugins.is_dir()
