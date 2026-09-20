from __future__ import annotations

import json

from computer.linux import screen


def computer_screen(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "list_monitors")).lower()
    if operation == "list_monitors":
        return json.dumps({"success": True, "monitors": [item.as_dict() for item in screen.list_monitors()],
                           "backends": screen.detect_backends(), "primary": (screen.get_primary_monitor().as_dict() if screen.get_primary_monitor() else None)})
    if operation == "capture":
        index = int(params.get("monitor", screen.get_primary_monitor().index if screen.get_primary_monitor() else 1))
        result = screen.capture_monitor(index, float(params.get("timeout", 5)))
        return json.dumps(result.as_dict())
    if operation == "capture_all":
        return json.dumps({"success": True, "frames": [item.as_dict() for item in screen.capture_all_monitors(float(params.get("timeout", 5)))]})
    return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": "supported operations: list_monitors, capture, capture_all"})


TOOL = {"name": "computer_screen", "description": "List Linux monitors and capture a selected or all screens with frame diagnostics.",
        "risk_level": "L0", "supports_verification": True, "reversible": True,
        "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING"}, "monitor": {"type": "NUMBER"}, "timeout": {"type": "NUMBER"}}, "required": ["operation"]},
        "handler": computer_screen}