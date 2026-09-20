"""Controlled terminal execution exposed as a discovered Dobby action."""
from __future__ import annotations

import json
from pathlib import Path

from core.execution import run_command
from security.audit import record
from security.policy import classify


def terminal_execute(parameters: dict, **_) -> str:
    params = parameters or {}
    command = params.get("command", [])
    if isinstance(command, str):
        return "Provide command as an argument list; shell parsing is disabled for safety."
    if not isinstance(command, list) or not command:
        return "No command provided."
    decision = classify("terminal_execute", params)
    if decision.requires_confirmation:
        from core import confirm as confirm_gate

        def run_after_confirmation() -> str:
            return _execute(command, params, decision.level, "confirmed")

        return confirm_gate.request(
            "Run privileged or destructive command",
            " ".join(command),
            run_after_confirmation,
        )
    return _execute(command, params, decision.level, "not_required")


def _execute(command: list[str], params: dict, level: int, confirmation_state: str) -> str:
    result = run_command(command, params.get("working_directory"), params.get("timeout"), params.get("environment"))
    record(user_request=params.get("user_request", ""), selected_tool="terminal_execute",
           command=command, working_directory=params.get("working_directory"),
           risk_level=f"L{level}", confirmation_state=confirmation_state,
           result=result.success, exit_code=result.exit_code, errors=result.stderr,
           duration=result.duration)
    return json.dumps(result.as_dict(), ensure_ascii=True)


TOOL = {
    "name": "terminal_execute",
    "description": "Execute a safe local command and return actual stdout, stderr, exit code, and duration. Use an argument array; shell parsing and privileged commands are not allowed.",
    "parameters": {"type": "OBJECT", "properties": {
        "command": {"type": "ARRAY", "items": {"type": "STRING"}},
        "working_directory": {"type": "STRING"},
        "timeout": {"type": "NUMBER"},
        "environment": {"type": "OBJECT"},
    }, "required": ["command"]},
    "handler": terminal_execute,
}