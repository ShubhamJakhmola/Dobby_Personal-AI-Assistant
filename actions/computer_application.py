from __future__ import annotations

import json

from computer.linux import applications
from security.audit import record


def computer_application(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "discover")).lower()
    name = str(params.get("application", "")).strip()
    if operation == "discover":
        return json.dumps({"success": True, "status": "completed", "applications": applications.discover(), "verified": True})
    if not name:
        return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": "application is required"})
    if operation == "find":
        return json.dumps({"success": True, "status": "completed", "application": applications.find(name), "verified": True})
    if operation == "launch":
        result = applications.launch(name, params.get("wait", 1))
    elif operation in {"is_running", "status"}:
        pids = applications.is_running(name)
        result = {"success": True, "status": "completed", "application": name, "pids": pids, "running": bool(pids), "verified": True}
    elif operation == "close":
        result = applications.close(name, params.get("timeout", 5))
    else:
        return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": "supported operations: discover, find, launch, is_running, close"})
    record(selected_tool="computer_application", command=operation, risk_level="L1", result=result.get("success", False),
           verification=result.get("verified", False), application=name)
    return json.dumps(result)


TOOL = {"name": "computer_application", "description": "Discover, launch, inspect, and close Linux applications with process verification.",
        "risk_level": "L1", "supports_verification": True, "reversible": True,
        "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING"}, "application": {"type": "STRING"}, "wait": {"type": "NUMBER"}, "timeout": {"type": "NUMBER"}}, "required": ["operation"]},
        "handler": computer_application}