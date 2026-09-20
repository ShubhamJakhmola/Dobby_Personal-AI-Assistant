from __future__ import annotations

from agent.executor import ActionResult, execute
from agent.planner import PlanStep


MAX_RECOVERY_ATTEMPTS = 2


def recover(step: PlanStep, first: ActionResult) -> ActionResult:
    result = first
    limit = min(max(0, step.retries), MAX_RECOVERY_ATTEMPTS)
    for attempt in range(2, limit + 2):
        if result.success:
            break
        result.status = "recovering"
        result = execute(step, attempts=attempt)
    return result