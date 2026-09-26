"""Dobby self-model: introspection without pretending to be conscious."""
from __future__ import annotations

import json
import platform

from computer.state import get_state


def dobby_self(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "status")).lower().strip()
    state = get_state().snapshot()
    if operation == "status":
        return json.dumps({
            "identity": "Dobby",
            "role": "local computer-control AI assistant and orchestrator",
            "reasoning_provider": "configured model provider",
            "platform": platform.platform(),
            "current_task": state.get("task_goal"),
            "computer_state": state,
            "capability_model": "skills + tools + OS adapters + browser/computer control",
            "consciousness": {
                "literal": False,
                "implemented": "persistent self-model, state awareness, task awareness, capability awareness, and metacognitive execution records",
            },
        }, ensure_ascii=True)
    if operation == "limitations":
        return json.dumps({
            "cannot_claim": [
                "human consciousness or subjective experience",
                "unrestricted control of every third-party service regardless of permissions",
                "guaranteed compatibility with every application on every OS",
            ],
            "design_goal": "broad cross-platform control with explicit capability detection, safe execution, verification, and recovery",
        }, ensure_ascii=True)
    return json.dumps({"success": False, "error": "Supported operations: status, limitations."})


TOOL = {
    "name": "dobby_self",
    "description": "Inspect Dobby's current self-model, task state, computer state, and explicit capability limitations. This is introspection, not a claim of literal consciousness.",
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING", "description": "status or limitations"},
    }, "required": ["operation"]},
    "handler": dobby_self,
    "risk_level": "L0",
    "reversible": True,
    "supports_verification": True,
}
