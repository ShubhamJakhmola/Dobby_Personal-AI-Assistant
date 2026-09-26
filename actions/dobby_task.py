"""Explicit task/context control for multi-step JARVIS-style interaction."""
from __future__ import annotations
import json
import uuid
from computer.state import get_state, update_state


def dobby_task(parameters: dict, **_) -> str:
    p = parameters or {}
    op = str(p.get("operation", "status")).lower().strip()
    state = get_state()
    if op in {"start", "set_goal"}:
        goal = str(p.get("goal", "")).strip()
        if not goal:
            return json.dumps({"success": False, "error": "goal is required"})
        task_id = state.task_id or f"task-{uuid.uuid4().hex[:10]}"
        update_state(task_id=task_id, task_goal=goal, metadata={**state.metadata, "task_status": "running"})
        return json.dumps({"success": True, "task_id": task_id, "goal": goal, "status": "running"})
    if op in {"complete", "finish"}:
        update_state(metadata={**state.metadata, "task_status": "completed"})
        return json.dumps({"success": True, "task_id": state.task_id, "status": "completed"})
    if op in {"cancel", "reset"}:
        update_state(task_id=None, task_goal=None, metadata={})
        return json.dumps({"success": True, "status": "idle"})
    if op == "status":
        return json.dumps({"success": True, "task": state.snapshot()}, ensure_ascii=True)
    return json.dumps({"success": False, "error": "supported operations: start, set_goal, status, complete, cancel"})


TOOL = {
    "name": "dobby_task",
    "description": "Start, inspect, complete, or reset Dobby's persistent multi-step task context. Use when a user starts a goal and later refers to 'it', 'that', or the current task.",
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING"}, "goal": {"type": "STRING"}
    }, "required": ["operation"]},
    "handler": dobby_task, "risk_level": "L0", "supports_verification": True,
}
