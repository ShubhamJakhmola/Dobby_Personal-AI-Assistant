from __future__ import annotations

from computer.linux.screen import detect_backends
from computer.platform import current_platform


def capture_status() -> dict:
    backends = detect_backends()
    return {"available": bool(backends), "backends": backends,
            "status": "available" if backends else "unavailable",
            "platform": current_platform(),
            "analysis": "provider-dependent", "observation": "foundation-only"}