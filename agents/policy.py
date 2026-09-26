from __future__ import annotations

from security.policy import classify


def validate_agent_scope(spec, action_registry) -> tuple[bool, str]:
    if spec.agent_type not in {"temporary", "persistent"}:
        return False, "agent type must be temporary or persistent"
    if spec.agent_type == "temporary" and spec.persistent:
        return False, "temporary agents cannot be persistent"
    if spec.limits.get("max_runtime_seconds", 0) <= 0 or spec.limits.get("max_steps", 0) <= 0:
        return False, "agent limits must be positive"
    for capability in spec.capabilities:
        if capability.startswith("terminal"):
            decision = classify("terminal_execute", {"command": ["agent"]})
            if not decision.allowed:
                return False, "agent terminal scope is policy denied"
    return True, "agent scope accepted"