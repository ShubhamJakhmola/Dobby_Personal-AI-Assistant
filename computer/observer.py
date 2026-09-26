"""Cheap world-state observation with optional visual capture."""
from __future__ import annotations

import platform
import subprocess
from typing import Any

from computer.state import get_state, observe_desktop, update_state


def observe(include_screen: bool = False) -> dict[str, Any]:
    state = observe_desktop()
    state["platform"] = platform.system()
    state["computer_state"] = get_state().snapshot()

    if platform.system() == "Windows":
        try:
            p = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True,
                               text=True, timeout=3)
            state["process_count"] = len([x for x in p.stdout.splitlines() if x.strip()]) if p.returncode == 0 else None
        except Exception:
            pass
    elif platform.system() in {"Linux", "Darwin"}:
        try:
            p = subprocess.run(["ps", "-A"], capture_output=True, text=True, timeout=3)
            state["process_count"] = max(0, len(p.stdout.splitlines()) - 1) if p.returncode == 0 else None
        except Exception:
            pass

    if include_screen:
        try:
            from actions.computer_control import _screenshot
            state["screen"] = {"success": True, "path": _screenshot()}
        except Exception as exc:
            state["screen"] = {"success": False, "error": str(exc)}

    update_state(last_observation=state)
    return state
