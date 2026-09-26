"""Shared structured subprocess execution for Dobby actions."""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class ExecutionStatus(str, Enum):
    PLANNED = "planned"
    WAITING_CONFIRMATION = "waiting_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    VERIFICATION_FAILED = "verification_failed"
    RECOVERING = "recovering"


@dataclass
class ExecutionResult:
    success: bool
    exit_code: int | None
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False
    action: str = "terminal.execute"
    status: str = ""
    verified: bool = False
    verification: dict | None = None
    error: str | None = None
    error_category: str | None = None

    def __post_init__(self):
        if not self.status:
            self.status = (ExecutionStatus.TIMEOUT.value if self.timed_out else
                           ExecutionStatus.COMPLETED.value if self.success else
                           ExecutionStatus.FAILED.value)
        if self.error is None and not self.success:
            self.error = self.stderr or "command failed"

    def as_dict(self) -> dict:
        return asdict(self)


def run_command(
    command: list[str],
    working_directory: str | Path | None = None,
    timeout: float | None = None,
    environment: dict[str, str] | None = None,
    action: str = "terminal.execute",
    cancel_event=None,
) -> ExecutionResult:
    """Run an argv command without a shell and return the actual result."""
    if not command or not all(isinstance(part, str) for part in command):
        raise ValueError("command must be a non-empty list of strings")

    started = time.monotonic()
    env = None
    if environment is not None:
        env = os.environ.copy()
        env.update({str(key): str(value) for key, value in environment.items()})

    process = None
    try:
        process = subprocess.Popen(
            command,
            cwd=str(working_directory) if working_directory else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        deadline = started + timeout if timeout is not None else None
        while True:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                stdout, stderr = process.communicate()
                return ExecutionResult(False, process.returncode, stdout, stderr,
                                       time.monotonic() - started, action=action,
                                       status=ExecutionStatus.CANCELLED.value,
                                       error="execution cancelled", error_category="cancelled")
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            try:
                stdout, stderr = process.communicate(timeout=min(0.1, remaining) if remaining is not None else 0.1)
                break
            except subprocess.TimeoutExpired:
                if deadline is not None and time.monotonic() >= deadline:
                    process.kill()
                    stdout, stderr = process.communicate()
                    return ExecutionResult(False, None, stdout, stderr,
                                           time.monotonic() - started, True, action,
                                           ExecutionStatus.TIMEOUT.value, error="command timed out",
                                           error_category="timeout")
        return ExecutionResult(
            success=process.returncode == 0,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration=time.monotonic() - started,
            action=action,
            error_category=None if process.returncode == 0 else "command_failed",
        )
    except OSError as exc:
        return ExecutionResult(
            success=False,
            exit_code=None,
            stdout="",
            stderr=str(exc),
            duration=time.monotonic() - started,
            action=action,
            error=str(exc),
            error_category="command_not_found" if getattr(exc, "errno", None) == 2 else "permission_denied" if getattr(exc, "errno", None) == 13 else "unknown_error",
        )