from __future__ import annotations

from agent.verification.base import VerificationResult


def verify_command_output(result, expected_stdout: str | None = None, expected_exit_code: int = 0) -> VerificationResult:
    actual = result.as_dict() if hasattr(result, "as_dict") else result
    stdout_ok = expected_stdout is None or actual.get("stdout", "") == expected_stdout
    verified = actual.get("exit_code") == expected_exit_code and stdout_ok
    return VerificationResult(verified, "command_output", {"exit_code": expected_exit_code, "stdout": expected_stdout}, actual,
                              "command output matches" if verified else "command output does not match")