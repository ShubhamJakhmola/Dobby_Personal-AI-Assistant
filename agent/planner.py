from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PlanStep:
    name: str
    action: Callable[[dict], Any]
    arguments: dict = field(default_factory=dict)
    expected: Callable[[Any], bool] | None = None
    verifier: Callable[[Any], Any] | None = None
    retries: int = 0
    depends_on: list[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    goal: str
    steps: list[PlanStep]


class Planner:
    """Build plans from trusted runtime capabilities, not invented commands."""

    def from_steps(self, goal: str, steps: list[PlanStep]) -> TaskPlan:
        return TaskPlan(goal=goal, steps=steps)