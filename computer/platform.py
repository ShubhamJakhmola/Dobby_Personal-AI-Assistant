from __future__ import annotations

import platform
import os
import shutil


def current_platform() -> str:
    return platform.system().lower()


def adapter_status() -> dict:
    name = current_platform()
    return {"platform": name, "linux_adapter": name == "linux", "status": "available" if name == "linux" else "unsupported"}


def environment() -> dict:
    name = current_platform()
    display_server = "Wayland" if os.environ.get("WAYLAND_DISPLAY") else "X11" if os.environ.get("DISPLAY") else "unknown"
    desktop = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "unknown"
    return {
        "os": platform.system(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "desktop": desktop,
        "display_server": display_server,
        "DISPLAY": bool(os.environ.get("DISPLAY")),
        "WAYLAND_DISPLAY": bool(os.environ.get("WAYLAND_DISPLAY")),
        "tools": {tool: bool(shutil.which(tool)) for tool in ("wmctrl", "xdotool", "ydotool", "grim", "slurp", "xrandr")},
    }