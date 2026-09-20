from __future__ import annotations

from security.policy import classify


class ClientExecutor:
    def __init__(self, local_capabilities=None):
        self.local_capabilities = local_capabilities or {}

    def execute(self, task, *, device=None) -> dict:
        decision = classify(task.capability, task.parameters)
        if not decision.allowed:
            return {"status": "BLOCKED", "reason": decision.reason, "requires_confirmation": decision.requires_confirmation}
        if task.capability not in self.local_capabilities:
            return {"status": "BLOCKED", "reason": f"capability {task.capability} unavailable"}
        return {"status": "COMPLETED", "stdout": f"{task.capability}:{task.action} ok", "stderr": "", "exit_code": 0}
