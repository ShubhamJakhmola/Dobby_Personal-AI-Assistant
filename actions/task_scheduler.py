"""Linux user-level cron scheduler with verification."""
from __future__ import annotations

import json
import platform
import shlex
import shutil
import subprocess
from pathlib import Path

from scheduler.cron import CronScheduler
from core.execution import run_command
from security.audit import record

_MARKER = "# dobby-task:"


def _read_crontab() -> list[str]:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1) or (result.stderr.strip() and "no crontab" not in result.stderr.lower()):
        raise RuntimeError(result.stderr.strip() or "could not read crontab")
    return result.stdout.splitlines() if result.returncode == 0 else []


def _write_crontab(lines: list[str]) -> None:
    payload = "\n".join(lines).rstrip() + "\n"
    result = subprocess.run(["crontab", "-"], input=payload, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "could not install crontab")


def _entries() -> dict[str, dict]:
    entries = {}
    for line in _read_crontab():
        if _MARKER not in line:
            continue
        prefix, _, name = line.partition(_MARKER)
        name = name.strip()
        entries[name] = {"name": name, "schedule": prefix.strip(), "enabled": not line.lstrip().startswith("#")}
    return entries


def task_scheduler(parameters: dict, **_) -> str:
    if platform.system() != "Linux":
        return "Task scheduling is currently implemented for Linux only."
    if not shutil.which("crontab"):
        return "Linux scheduler unavailable: install cron/cronie to provide crontab."
    params = parameters or {}
    scheduler = CronScheduler()
    operation = str(params.get("operation", "list")).lower().strip()
    name = str(params.get("name", "")).strip()
    try:
        lines = _read_crontab()
        entries = scheduler.list()
        if operation in {"list", "get"}:
            value = entries if operation == "list" else entries.get(name, {"error": "task not found"})
            return json.dumps(value)
        if operation in {"create", "update"}:
            schedule = str(params.get("schedule", "")).strip()
            command = params.get("command")
            if not name or not schedule or not isinstance(command, list) or not command:
                return "Create requires name, five-field cron schedule, and command argument list."
            if len(schedule.split()) != 5 or not all(isinstance(part, str) for part in command):
                return "Schedule must contain exactly five cron fields and command must be an argument list."
            executable = Path(command[0]).expanduser()
            if not executable.exists() or not executable.is_file():
                return f"Command executable does not exist: {executable}"
            lines = [line for line in lines if _MARKER + name not in line]
            rendered = " ".join(shlex.quote(part) for part in command)
            lines.append(f"{schedule} {rendered} {_MARKER}{name}")
            _write_crontab(lines)
            verified = scheduler.verify(name, schedule, command)
            record(selected_tool="task_scheduler", command="create", risk_level="L2",
                   confirmation_state="not_required", result=verified, exit_code=0 if verified else 1)
            return json.dumps({"success": verified, "task": scheduler.list().get(name)})
        if operation in {"delete", "disable", "enable"}:
            if name not in entries:
                return json.dumps({"success": False, "error": "task not found"})
            updated = []
            for line in lines:
                if _MARKER + name not in line:
                    updated.append(line)
                    continue
                if operation == "delete":
                    continue
                uncommented = line.lstrip("# ")
                updated.append(uncommented if operation == "enable" else "# " + uncommented)
            _write_crontab(updated)
            return json.dumps({"success": True, "task": scheduler.list().get(name)})
        if operation in {"run", "run_now"}:
            task = entries.get(name)
            if not task:
                return json.dumps({"success": False, "error": "task not found"})
            result = run_command(task["command"], timeout=params.get("timeout"), action="scheduler.run_now")
            return json.dumps({"success": result.success, "execution": result.as_dict(),
                               "verified": result.success})
        return "Supported operations: create, delete, update, enable, disable, run, list, get."
    except (OSError, RuntimeError) as exc:
        return json.dumps({"success": False, "error": str(exc)})


TOOL = {"name": "task_scheduler", "description": "Create, inspect, enable, disable, and delete verified Linux user cron tasks without root privileges.",
        "parameters": {"type": "OBJECT", "properties": {
            "operation": {"type": "STRING"}, "name": {"type": "STRING"},
            "schedule": {"type": "STRING"}, "command": {"type": "ARRAY", "items": {"type": "STRING"}}
        }, "required": ["operation"]}, "handler": task_scheduler}