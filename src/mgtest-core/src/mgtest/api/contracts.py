"""Reusable checks for definition packages and their test suites."""

from __future__ import annotations

from inspect import isabstract

from mgtest.api.resource import ResourceSpec
from mgtest.api.test import TestSpec


def assert_definition_contract(definition_class: type[ResourceSpec] | type[TestSpec]) -> None:
    """Assert that one registered resource or test class satisfies the SDK contract."""
    assert not isabstract(definition_class)
    assert definition_class.__doc__ and definition_class.__doc__.strip()
    assert definition_class.type_name()
    assert definition_class.model_json_schema()

    # Required fields are intentionally definition-specific, so a generic contract
    # cannot construct an instance safely. Each package's unit tests exercise its
    # factory with valid input; the common contract verifies the declared factory.
    assert "create_instance" in definition_class.__dict__
