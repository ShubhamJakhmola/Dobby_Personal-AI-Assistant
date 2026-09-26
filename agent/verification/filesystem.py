from __future__ import annotations

from pathlib import Path

from agent.verification.base import VerificationResult


def verify_file_exists(path: str, expected_contents: str | None = None) -> VerificationResult:
    target = Path(path).expanduser()
    exists = target.is_file()
    contents_ok = expected_contents is None or (exists and target.read_text(encoding="utf-8") == expected_contents)
    return VerificationResult(exists and contents_ok, "file_exists", str(target),
                              str(target) if exists else None,
                              "file and contents match" if exists and contents_ok else "file or contents do not match")