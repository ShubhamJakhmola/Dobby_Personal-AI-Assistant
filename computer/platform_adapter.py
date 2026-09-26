"""Cross-platform OS primitives used by Dobby's higher-level skills.

The adapter deliberately exposes small, reversible operations.  Higher-level
planning belongs to Dobby; this module only performs platform-specific work.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any


def os_name() -> str:
    return platform.system()


def environment() -> dict[str, Any]:
    system = os_name()
    display = "Wayland" if os.environ.get("WAYLAND_DISPLAY") else "X11" if os.environ.get("DISPLAY") else "unknown"
    return {
        "os": system,
        "release": platform.release(),
        "architecture": platform.machine(),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or None,
        "display_server": display,
    }


def _windows_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    try:
        import winreg
        candidates = [
            rf"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{name}.exe",
            rf"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{name}.exe",
        ]
        for path in candidates:
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    key = winreg.OpenKey(hive, path)
                    value = winreg.QueryValue(key, None)
                    winreg.CloseKey(key)
                    if value:
                        return value.strip().strip('"').split('"')[0]
                except Exception:
                    continue
    except Exception:
        pass
    return None


def find_application(name: str) -> dict[str, Any]:
    requested = str(name or "").strip()
    if not requested:
        return {"found": False, "error": "application is required"}
    candidates = [requested]
    aliases = {
        "chrome": ["google-chrome", "chrome"],
        "google chrome": ["chrome", "google-chrome"],
        "edge": ["msedge", "microsoft-edge"],
        "microsoft edge": ["msedge", "microsoft-edge"],
        "firefox": ["firefox"],
        "vlc": ["vlc"],
        "notepad": ["notepad"],
        "calculator": ["calc", "gnome-calculator", "kcalc"],
        "file explorer": ["explorer", "nautilus", "dolphin", "thunar"],
    }
    candidates.extend(aliases.get(requested.lower(), []))
    for candidate in candidates:
        found = _windows_executable(candidate) if os_name() == "Windows" else shutil.which(candidate)
        if found:
            return {"found": True, "application": requested, "executable": found}
    return {"found": False, "application": requested, "candidates": candidates}


def launch_application(name: str, args: list[str] | None = None, wait: float = 0.8) -> dict[str, Any]:
    info = find_application(name)
    if not info.get("found"):
        return info | {"success": False, "error_category": "application_not_found"}
    executable = str(info["executable"])
    argv = [executable] + [str(x) for x in (args or [])]
    try:
        kwargs: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os_name() == "Windows":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(argv, **kwargs)
        if wait:
            import time
            time.sleep(min(max(float(wait), 0), 5))
        return {"success": True, "application": name, "executable": executable, "pid": proc.pid}
    except Exception as exc:
        return {"success": False, "application": name, "error_category": "launch_failed", "error": str(exc)}


def open_path(path: str) -> dict[str, Any]:
    target = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.exists(target):
        return {"success": False, "error_category": "path_not_found", "path": target}
    try:
        system = os_name()
        if system == "Windows":
            os.startfile(target)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "path": target}
    except Exception as exc:
        return {"success": False, "error_category": "open_failed", "path": target, "error": str(exc)}
