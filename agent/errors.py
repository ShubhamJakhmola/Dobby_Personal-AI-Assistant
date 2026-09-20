from __future__ import annotations


def classify_error(error: str, *, timed_out: bool = False) -> str:
    if timed_out:
        return "timeout"
    text = str(error or "").lower()
    if "not found" in text or "no such file" in text:
        return "command_not_found"
    if "permission" in text or "access denied" in text:
        return "permission_denied"
    if "invalid" in text or "usage:" in text:
        return "invalid_arguments"
    if "network" in text or "connection" in text:
        return "network_error"
    return "unknown_error"