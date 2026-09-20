from __future__ import annotations

import importlib.util
import platform

from computer.platform import adapter_status
from vision.capture import capture_status


def collect(registry) -> dict:
    unavailable = []
    for record in getattr(registry, "_all_records", []):
        if not record.valid and record.error:
            unavailable.append({"name": record.name, "error": record.error})
    computer = adapter_status()
    capture = capture_status()
    return {
        "platform": platform.system(),
        "brain": "Gemini",
        "execution": "available",
        "verification": "available",
        "recovery": "available",
        "scheduler": "cron" if platform.system() == "Linux" else "linux-only",
        "browser": "available" if importlib.util.find_spec("playwright") else "optional/unavailable",
        "computer": computer,
        "screen_capture": capture,
        "unavailable_actions": unavailable,
        "legacy_actions": "tracked by compatibility adapter",
    }