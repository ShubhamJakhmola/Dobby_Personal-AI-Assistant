"""Dobby master orchestration facade.

This is intentionally model-neutral.  A reasoning provider supplies a sequence
of proposed actions; this class keeps task/world context and sends every action
through the same computer execution boundary.
"""
from __future__ import annotations

import uuid
from typing import Any

from computer.state import get_state, update_state
from computer.observer import observe
from computer.engine import ComputerEngine


class DobbyOrchestrator:
    def __init__(self, registry, policy=None, confirmer=None):
        self.engine = ComputerEngine(registry, policy=policy, confirmer=confirmer)

    def start_task(self, goal: str) -> dict[str, Any]:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        update_state(task_id=task_id, task_goal=goal, task_status="running")
        return {"task_id": task_id, "goal": goal, "state": observe()}

    def act(self, action: str, parameters: dict[str, Any] | None = None,
            verify: bool = True, retries: int = 1) -> dict[str, Any]:
        result = self.engine.execute(action, parameters, goal=get_state().task_goal or "",
                                     verify=verify, retries=retries)
        if result.get("success"):
            update_state(task_status="running")
        else:
            update_state(task_status="needs_recovery")
        return result

    def finish(self, success: bool = True) -> dict[str, Any]:
        update_state(task_status="completed" if success else "failed")
        return get_state().snapshot()
