from __future__ import annotations

from typing import Any

from agent.planner import PlanStep
from agent.verification.base import VerificationResult


def verify(step: PlanStep, value: Any) -> VerificationResult:
    if step.verifier is not None:
        result = step.verifier(value)
        if isinstance(result, VerificationResult):
            return result
        return VerificationResult(bool(result), "custom", True, result)
    if step.expected is not None:
        actual = bool(step.expected(value))
        return VerificationResult(actual, "expected_predicate", True, actual,
                                  "predicate passed" if actual else "predicate failed")
    return VerificationResult(False, "verification_required", True, value,
                              "no verifier was supplied")