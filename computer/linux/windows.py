from __future__ import annotations

import shutil
import subprocess


def _tool() -> str | None:
    return shutil.which("wmctrl") or shutil.which("xdotool")


def list_windows() -> list[dict]:
    if shutil.which("wmctrl"):
        result = subprocess.run(["wmctrl", "-l", "-p"], capture_output=True, text=True, timeout=5, check=False)
        windows = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 5:
                windows.append({"id": parts[0], "desktop": parts[1], "pid": int(parts[2]), "title": parts[4]})
        return windows
    return []


def active_window() -> dict:
    if shutil.which("xdotool"):
        wid = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        title = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=5, check=False).stdout.strip()
        if wid:
            return {"id": wid, "title": title}
    return {"available": False, "error_category": "capability_unavailable", "error": "wmctrl or xdotool unavailable"}


def focus(window_id: str) -> dict:
    tool = _tool()
    if not tool:
        raise RuntimeError("window focus unavailable: install wmctrl or xdotool")
    command = ["wmctrl", "-i", "-a", str(window_id)] if tool == shutil.which("wmctrl") else ["xdotool", "windowactivate", str(window_id)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    return {"focused": result.returncode == 0, "window_id": window_id, "stderr": result.stderr.strip()}