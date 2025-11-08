"""Stable API for mgtest resource, test, and integration authors."""

from mgtest.api.contracts import assert_definition_contract
from mgtest.api.events import ExecutionOutcome, LifecycleEvent, LifecycleListener
from mgtest.api.resource import ResourceInstance, ResourceScope, ResourceSpec
from mgtest.api.retry import retry
from mgtest.api.test import TestInstance, TestSpec

__all__ = [
    "ExecutionOutcome",
    "LifecycleEvent",
    "LifecycleListener",
    "ResourceInstance",
    "ResourceScope",
    "ResourceSpec",
    "TestInstance",
    "TestSpec",
    "assert_definition_contract",
    "retry",
]
