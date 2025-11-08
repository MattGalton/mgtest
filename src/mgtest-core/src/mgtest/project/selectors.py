"""Public selector syntax for suites and checks."""


def split_check_selector(selector: str) -> tuple[str, str] | None:
    """Split ``suite/path/check`` into its suite path and check name.

    A bare name is intentionally left unresolved so callers can report ambiguity.
    """
    selector = selector.strip("/")
    if "/" not in selector:
        return None
    suite, name = selector.rsplit("/", 1)
    return (suite or ".", name) if name else None


def format_check_selector(suite: str, name: str) -> str:
    """Return the canonical user-facing selector for a check."""
    return name if suite == "." else f"{suite}/{name}"
