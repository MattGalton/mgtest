"""Public façade for editor-independent mgtest YAML analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .completion import CompletionProvider
from .context import AnalysisContext
from .fixes import FixProvider
from .navigation import NavigationProvider
from .types import Diagnostic
from .validation import ValidationProvider


class AnalysisService:
    """Delegate editor requests to focused analysis providers."""

    def __init__(self, root: Path | None = None, extra_paths: list[Path] | None = None):
        self.context = AnalysisContext(root, extra_paths)
        self.completion = CompletionProvider(self.context)
        self.fixes = FixProvider(self.context)
        self.navigation = NavigationProvider(self.context)
        self.validation = ValidationProvider(self.context)

    def analyse(self, path: Path, source: str) -> list[Diagnostic]:
        return self.validation.analyse(path, source)

    def completions(
        self, path: Path, source: str, line: int, character: int
    ) -> list[dict[str, Any]]:
        return self.completion.complete(path, source, line, character)

    def hover(self, path: Path, source: str, line: int, character: int) -> str | None:
        return self.navigation.hover(path, source, line, character)

    def definitions(self, path: Path, source: str, line: int, character: int) -> list[Path]:
        return self.navigation.definitions(path, source, line, character)

    def references(
        self, path: Path, source: str, line: int, character: int
    ) -> list[dict[str, Any]]:
        return self.navigation.references(path, source, line, character)

    def symbols(self, path: Path, source: str) -> list[dict[str, Any]]:
        return self.navigation.symbols(path, source)

    def code_actions(
        self, path: Path, source: str, selection: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return self.fixes.actions(path, source, selection)
