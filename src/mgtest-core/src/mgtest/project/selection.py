"""Shared CLI selection rules for a suite or one check."""

from mgtest.project.selectors import format_check_selector, split_check_selector


def select(project, selector: str | None) -> None:
    """Apply a suite, qualified check, or unambiguous check-name selection."""
    if selector is None:
        return
    suite = _suite_id(selector)
    if suite in project.suites:
        project.selection = suite
        return
    matches = [
        definition.id
        for definition in project.definitions.values()
        if definition.kind == "tests" and _matches_test(definition, selector)
    ]
    if not matches:
        raise ValueError(f"Unknown suite or test '{selector}'")
    if len(matches) > 1:
        choices = ", ".join(
            format_check_selector(
                project.definitions[identity].suite, project.definitions[identity].name
            )
            for identity in matches
        )
        raise ValueError(f"Test '{selector}' is ambiguous. Choose one of: {choices}")
    project.selected_tests = frozenset(matches)


def _suite_id(value: str) -> str:
    return value.strip("/") or "."


def _matches_test(definition, selector: str) -> bool:
    if parsed := split_check_selector(selector):
        suite, name = parsed
        return definition.suite == suite and definition.name == name
    return definition.name == selector
