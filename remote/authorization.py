from __future__ import annotations

from security.policy import classify


class AuthorizationPolicy:
    def __init__(self, capability_registry=None):
        self.capability_registry = capability_registry or {}

    def _caps(self, device):
        raw = device.get("capabilities", []) if isinstance(device, dict) else getattr(device, "capabilities", [])
        caps = set()
        for item in raw:
            if isinstance(item, dict):
                caps.add(item.get("id") or item.get("name"))
            else:
                caps.add(getattr(item, "id", getattr(item, "name", None)))
        return {cap for cap in caps if cap}

    def authorize(self, device, task) -> tuple[bool, str]:
        if device is None:
            return False, "device not found"
        device_caps = self._caps(device)
        if task.capability not in device_caps:
            return False, f"device does not advertise capability {task.capability}"
        action_name = f"{task.capability}_{task.action}" if task.action else str(task.capability)
        decision = classify(action_name, task.parameters)
        if not decision.allowed:
            return False, f"policy denied: {decision.reason}"
        if decision.requires_confirmation:
            return False, "sensitive remote action requires existing Dobby confirmation flow"
        return True, "authorized"
