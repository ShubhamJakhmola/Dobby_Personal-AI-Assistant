from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.planner import PlanStep
from agent.errors import classify_error


@dataclass
class ActionResult:
    step: str
    success: bool
    value: Any = None
    error: str = ""
    attempts: int = 1
    status: str = "executing"
    verified: bool = False
    verification: dict | None = None
    error_category: str | None = None

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def execute(step: PlanStep, attempts: int = 1) -> ActionResult:
    try:
        value = step.action(step.arguments)
        return ActionResult(step.name, True, value, attempts=attempts, status="completed")
    except Exception as exc:
        return ActionResult(step.name, False, error=str(exc), attempts=attempts,
                            status="failed", error_category=classify_error(str(exc)))