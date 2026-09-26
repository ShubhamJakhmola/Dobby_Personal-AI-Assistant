from __future__ import annotations

import socket

from agent.verification.base import VerificationResult


def verify_port_listening(host: str, port: int, timeout: float = 1.0) -> VerificationResult:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return VerificationResult(True, "port_listening", f"{host}:{port}", "listening", "connection succeeded")
    except OSError as exc:
        return VerificationResult(False, "port_listening", f"{host}:{port}", "unreachable", str(exc))