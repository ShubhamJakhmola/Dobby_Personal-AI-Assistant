from __future__ import annotations

import json

from computer.linux import windows


def computer_window(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "list")).lower()
    try:
        if operation == "list":
            data = windows.list_windows()
        elif operation == "get_active":
            data = windows.active_window()
        elif operation == "focus":
            data = windows.focus(str(params["window_id"]))
        else:
            return json.dumps({"success": False, "error_category": "invalid_arguments", "error": "supported operations: list, get_active, focus"})
        available = not (isinstance(data, dict) and data.get("available") is False)
        return json.dumps({"success": available, "status": "completed" if available else "failed", "data": data,
                           "verified": operation in {"get_active", "focus"} and available,
                           "error_category": None if available else data.get("error_category")})
    except Exception as exc:
        return json.dumps({"success": False, "status": "failed", "error_category": "capability_unavailable", "error": str(exc)})


TOOL = {"name": "computer_window", "description": "List, inspect, and focus Linux desktop windows when wmctrl or xdotool is available.",
        "risk_level": "L1", "supports_verification": True, "reversible": True,
        "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING"}, "window_id": {"type": "STRING"}}, "required": ["operation"]},
        "handler": computer_window}