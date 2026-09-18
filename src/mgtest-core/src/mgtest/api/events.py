"""Structured execution events emitted by :class:`ExecutionSession`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

ExecutionKind = Literal["resource", "test"]
ExecutionPhase = Literal["setup", "run", "teardown"]
ExecutionStatus = Literal["started", "passed", "failed", "expected_failed"]


@dataclass(frozen=True)
class LifecycleEvent:
    """One lifecycle transition for a resource or check."""

    kind: ExecutionKind
    phase: ExecutionPhase
    status: ExecutionStatus
    identity: str
    type_name: str
    name: str
    error: BaseException | None = None


@dataclass(frozen=True)
class ExecutionOutcome:
    """The retained result of one resource setup or check execution."""

    kind: ExecutionKind
    identity: str
    status: Literal["passed", "failed"]
    value: object | None = None
    error: BaseException | None = None


LifecycleListener = Callable[[LifecycleEvent], None]
