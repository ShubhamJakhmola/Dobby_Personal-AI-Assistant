"""Cross-platform process inspection and verified lifecycle operations."""
from __future__ import annotations

import json
import subprocess
import time

import psutil

from security.audit import record
from security.policy import classify


def _matches(query: str):
    needle = query.lower().strip()
    return [proc for proc in psutil.process_iter(["pid", "name", "cmdline", "status", "memory_info"])
            if needle in (proc.info.get("name") or "").lower()
            or needle in " ".join(proc.info.get("cmdline") or []).lower()]


def process_manager(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "list")).lower().strip()
    query = str(params.get("query", "")).strip()
    if operation == "list":
        items = []
        for process in psutil.process_iter(["pid", "name", "status", "memory_info"]):
            try:
                items.append({"pid": process.info["pid"], "name": process.info["name"],
                              "status": process.info["status"],
                              "memory": process.info["memory_info"].rss if process.info["memory_info"] else 0,
                              "cpu": process.cpu_percent(interval=0.0)})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return json.dumps(items[:200])
    if operation == "start":
        command = params.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            return "Start requires a command argument list."
        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(min(float(params.get("wait", 0.2)), 5.0))
            running = psutil.pid_exists(process.pid)
            result = {"success": running, "pid": process.pid, "running": running}
            record(selected_tool="process_manager", command="start", risk_level="L1",
                   confirmation_state="not_required", result=running, exit_code=0 if running else 1)
            return json.dumps(result)
        except OSError as exc:
            return json.dumps({"success": False, "error": str(exc), "error_category": "command_not_found"})
    matches = _matches(query) if query else []
    if operation == "find":
        return json.dumps([{"pid": p.pid, "name": p.name(), "status": p.status()} for p in matches])
    if operation not in {"stop", "restart"}:
        return "Supported operations: list, find, stop, restart."
    if not matches:
        return f"No process matched '{query}'."
    decision = classify("process_manager", params)
    results = []
    for proc in matches:
        try:
            proc.terminate()
            proc.wait(timeout=float(params.get("timeout", 5)))
            stopped = not proc.is_running()
            if operation == "restart" and stopped:
                return json.dumps({"success": False, "message": "Restart requires an executable path; process was stopped."})
            results.append({"pid": proc.pid, "name": proc.name(), "stopped": stopped})
        except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied) as exc:
            results.append({"pid": proc.pid, "name": proc.info.get("name"), "stopped": False, "error": str(exc)})
    success = all(item["stopped"] for item in results)
    record(selected_tool="process_manager", command=operation, risk_level=f"L{decision.level}",
           confirmation_state="not_required", result=success, exit_code=0 if success else 1,
           errors="" if success else results)
    return json.dumps({"success": success, "operation": operation, "results": results})


TOOL = {"name": "process_manager", "description": "List, find, stop, and verify local processes.",
        "parameters": {"type": "OBJECT", "properties": {
            "operation": {"type": "STRING"}, "query": {"type": "STRING"}, "timeout": {"type": "NUMBER"}
        }, "required": ["operation"]}, "handler": process_manager}