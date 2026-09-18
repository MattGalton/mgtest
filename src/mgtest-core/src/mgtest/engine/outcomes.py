"""One policy for comparing a check's actual and expected outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ActualOutcome = Literal["passed", "failed"]
ExpectedOutcome = Literal["passed", "failed"]
OutcomeDisposition = Literal[
    "matched_pass",
    "matched_failure",
    "unexpected_failure",
    "unexpected_pass",
]


@dataclass(frozen=True)
class OutcomeAssessment:
    """The policy result adapters use to present one completed check."""

    expected: ExpectedOutcome
    actual: ActualOutcome
    disposition: OutcomeDisposition

    @property
    def matched(self) -> bool:
        """Whether the actual outcome fulfils the check declaration."""
        return self.disposition in {"matched_pass", "matched_failure"}

    @property
    def lifecycle_status(self) -> Literal["passed", "failed", "expected_failed"]:
        """Return the lifecycle status suitable for event listeners."""
        if self.disposition == "matched_failure":
            return "expected_failed"
        return self.actual


def assess_outcome(expected: ExpectedOutcome, actual: ActualOutcome) -> OutcomeAssessment:
    """Assess one actual check result against its declarative expectation."""
    disposition = {
        ("passed", "passed"): "matched_pass",
        ("failed", "failed"): "matched_failure",
        ("passed", "failed"): "unexpected_failure",
        ("failed", "passed"): "unexpected_pass",
    }[expected, actual]
    return OutcomeAssessment(expected, actual, disposition)
