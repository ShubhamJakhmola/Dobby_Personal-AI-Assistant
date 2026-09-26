"""Native Linux-first application launch and state verification."""
from __future__ import annotations

import json
import shutil
import subprocess
import time

import psutil

from security.audit import record


def _running(executable: str) -> list[dict]:
    needle = executable.lower()
    return [{"pid": p.pid, "name": p.info.get("name")}
            for p in psutil.process_iter(["name"])
            if needle in (p.info.get("name") or "").lower()]


def application_manager(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "status")).lower()
    application = str(params.get("application", "")).strip()
    if not application:
        return "No application provided."
    executable = shutil.which(application) or shutil.which(application.lower().replace(" ", "-"))
    if operation == "status":
        return json.dumps({"application": application, "running": _running(application)})
    if operation == "launch":
        if not executable:
            return json.dumps({"success": False, "application": application, "error": "executable not found"})
        try:
            subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(min(float(params.get("wait", 1)), 5.0))
        except OSError as exc:
            return json.dumps({"success": False, "error": str(exc)})
        running = _running(application)
        result = {"success": bool(running), "application": application, "running": running}
        record(selected_tool="application_manager", command="launch", risk_level="L1",
               confirmation_state="not_required", result=result["success"], exit_code=0 if result["success"] else 1)
        return json.dumps(result)
    return "Supported operations: launch, status. Use process_manager to stop an application."


TOOL = {"name": "application_manager", "description": "Launch an installed application and verify that its process is running, or inspect application state.",
        "parameters": {"type": "OBJECT", "properties": {
            "operation": {"type": "STRING"}, "application": {"type": "STRING"}, "wait": {"type": "NUMBER"}
        }, "required": ["operation", "application"]}, "handler": application_manager}