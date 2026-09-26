from __future__ import annotations

import json
import psutil

from computer.platform_adapter import find_application, launch_application
from security.audit import record


def _running(name: str) -> list[dict]:
    needle = name.lower().strip()
    rows = []
    for p in psutil.process_iter(["pid", "name", "status"]):
        try:
            pname = (p.info.get("name") or "")
            if needle in pname.lower():
                rows.append({"pid": p.pid, "name": pname, "status": p.info.get("status")})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return rows


def computer_application(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "find")).lower().strip()
    name = str(params.get("application", "")).strip()
    if operation == "find":
        return json.dumps(find_application(name), ensure_ascii=True)
    if not name:
        return json.dumps({"success": False, "error_category": "invalid_arguments", "error": "application is required"})
    if operation in {"is_running", "status"}:
        rows = _running(name)
        return json.dumps({"success": True, "application": name, "running": bool(rows), "processes": rows, "verified": True})
    if operation == "launch":
        result = launch_application(name, params.get("args") if isinstance(params.get("args"), list) else None, params.get("wait", 0.8))
        result["verified"] = bool(result.get("success") and result.get("pid"))
        record(selected_tool="computer_application", command="launch", risk_level="L1", result=result.get("success", False), verification=result.get("verified", False), application=name)
        return json.dumps(result, ensure_ascii=True)
    return json.dumps({"success": False, "error_category": "invalid_arguments", "error": "supported operations: find, discover, launch, is_running, status"})


TOOL = {
    "name": "computer_application",
    "description": "Cross-platform application discovery, launch, and running-state inspection. Prefer this over OS-specific launch commands.",
    "risk_level": "L1", "supports_verification": True, "reversible": True,
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING", "description": "find, discover, launch, is_running, or status"},
        "application": {"type": "STRING"},
        "args": {"type": "ARRAY", "items": {"type": "STRING"}},
        "wait": {"type": "NUMBER"},
    }, "required": ["operation"]},
    "handler": computer_application,
}
