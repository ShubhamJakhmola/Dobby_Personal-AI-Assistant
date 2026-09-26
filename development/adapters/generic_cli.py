from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from development.adapters.base import BaseCliAdapter
from development.models import CommandResult, CodingAgentResult, CodingAgentResultStatus, CodingTask
from development.redaction import redact_text


class GenericCliAdapter(BaseCliAdapter):
    id = "generic_cli"
    name = "Generic CLI"
    provider = "generic"
    supports_workspace = True
    supports_headless = True
    supports_noninteractive = True
    known_invocation_styles = ["executable args -- task via stdin or argv"]

    def __init__(self, executable: str | None = None, default_args: list[str] | None = None,
                 task_arg: bool = True, timeout: float = 300, output_limit: int = 12000):
        super().__init__(executable=executable, timeout=timeout)
        self.default_args = default_args or []
        self.task_arg = task_arg
        self.output_limit = output_limit
        self._process: subprocess.Popen | None = None
        self._last_command: CommandResult | None = None

    def _invocation_supported(self, executable: str) -> bool:
        return bool(executable)

    def _safe_env(self, workspace: Path) -> dict[str, str]:
        allowed = {"PATH", "PYTHONIOENCODING", "HOME", "USERPROFILE", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
        env = {key: os.environ[key] for key in allowed if os.environ.get(key)}
        env["PYTHONIOENCODING"] = "utf-8"
        env["HOME"] = str(workspace)
        return env

    def run_command(self, command: list[str], workspace: Path, timeout: float | None = None) -> CommandResult:
        started = time.monotonic()
        timeout = timeout if timeout is not None else self.timeout
        try:
            self._process = subprocess.Popen(command, cwd=workspace, env=self._safe_env(workspace),
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = self._process.communicate(timeout=timeout)
            truncated = len(stdout) > self.output_limit or len(stderr) > self.output_limit
            result = CommandResult("completed" if self._process.returncode == 0 else "failed", self._process.returncode,
                                   redact_text(stdout, limit=self.output_limit), redact_text(stderr, limit=self.output_limit),
                                   time.monotonic() - started, truncated=truncated, command=command, workspace=str(workspace))
        except subprocess.TimeoutExpired:
            self.stop()
            result = CommandResult("timed_out", None, duration=time.monotonic() - started, timed_out=True,
                                   command=command, workspace=str(workspace), errors=[f"timed out after {timeout}s"])
        except Exception as exc:
            result = CommandResult("failed", None, duration=time.monotonic() - started,
                                   command=command, workspace=str(workspace), errors=[str(exc)])
        finally:
            self._process = None
        self._last_command = result
        return result

    def start(self, workspace: Path, task: CodingTask) -> CodingAgentResult:
        valid, reason = task.validate()
        if not valid:
            return CodingAgentResult(CodingAgentResultStatus.BLOCKED, errors=[reason])
        executable = self._find_executable()
        if not executable:
            return CodingAgentResult(CodingAgentResultStatus.FAILED, errors=["executable not found"])
        command = [executable, *self.default_args]
        if self.task_arg:
            command.append(task.objective)
        result = self.run_command(command, workspace, task.timeout)
        status = CodingAgentResultStatus.COMPLETED_UNVERIFIED if result.success else (
            CodingAgentResultStatus.TIMED_OUT if result.timed_out else CodingAgentResultStatus.FAILED)
        summary = result.stdout.strip().splitlines()[0][:240] if result.stdout.strip() else result.status
        return CodingAgentResult(status, summary=summary, commands_executed=[command],
                                 errors=result.errors + ([result.stderr] if result.stderr and not result.success else []),
                                 raw_output_reference="captured_stdout_stderr",
                                 metadata={"command": result.as_dict()})

    def send_task(self, task: CodingTask) -> CodingAgentResult:
        return CodingAgentResult(CodingAgentResultStatus.BLOCKED, errors=["interactive sessions are not enabled"])

    def inspect_output(self) -> dict:
        return self._last_command.as_dict() if self._last_command else {"status": "not_started"}

    def stop(self) -> dict:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            return {"status": "stopped"}
        return {"status": "not_running"}

    def collect_result(self) -> CodingAgentResult:
        if not self._last_command:
            return CodingAgentResult(CodingAgentResultStatus.BLOCKED, errors=["no command has run"])
        return CodingAgentResult(CodingAgentResultStatus.COMPLETED_UNVERIFIED if self._last_command.success else CodingAgentResultStatus.FAILED,
                                 summary=self._last_command.status, metadata={"command": self._last_command.as_dict()})
