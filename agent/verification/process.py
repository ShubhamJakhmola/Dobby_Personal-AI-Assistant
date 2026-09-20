from __future__ import annotations

import psutil

from agent.verification.base import VerificationResult


def verify_process_running(name: str = "", pid: int | None = None) -> VerificationResult:
    matches = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if pid is not None and process.pid != pid:
            continue
        haystack = ((process.info.get("name") or "") + " " + " ".join(process.info.get("cmdline") or [])).lower()
        if not name or name.lower() in haystack:
            matches.append(process.pid)
    return VerificationResult(bool(matches), "process_running", pid or name, matches,
                              "matching process found" if matches else "no matching process")