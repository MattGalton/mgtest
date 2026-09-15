from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T", bound=type)


class PluginRegistry(Generic[T]):
    def __init__(self):
        self._registry: dict[str, T] = {}

    def register(self, key: str, value: T) -> None:
        """Register a definition class"""
        if key in self._registry:
            raise ValueError(f"Type '{key}' already registered")
        self._registry[key] = value

    def get(self, key: str) -> T | None:
        return self._registry.get(key)

    def keys(self) -> list[str]:
        """Get all registered types - needed for LSP"""
        return list(self._registry.keys())

    def items(self) -> Iterator[tuple[str, T]]:
        return self._registry.items()

    def values(self) -> Iterator[T]:
        return self._registry.values()

    def __getitem__(self, key: str) -> T:
        if key not in self._registry:
            raise KeyError(
                f"Type '{key}' not found. Available types: {list(self._registry.keys())}"
            )
        return self._registry[key]

    def __contains__(self, key: str) -> bool:
        return key in self._registry
