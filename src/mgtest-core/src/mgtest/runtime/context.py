"""The active run workspace for resource materialisation."""

from __future__ import annotations

import contextlib
import contextvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mgtest.runtime.runs import RunWorkspace

_workspace: contextvars.ContextVar[RunWorkspace | None] = contextvars.ContextVar(
    "mgtest_workspace", default=None
)


def current_workspace() -> RunWorkspace | None:
    """Return the workspace active while a resource is being materialized."""
    return _workspace.get()


@contextlib.contextmanager
def active_workspace(workspace: RunWorkspace):
    """Make a workspace available to resource implementations in this context."""
    token = _workspace.set(workspace)
    try:
        yield workspace
    finally:
        _workspace.reset(token)
