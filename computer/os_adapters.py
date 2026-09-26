"""Cross-platform OS capability adapters.

The adapter exposes a common contract while keeping platform-specific details
small.  It intentionally limits this layer to reversible/basic operations;
privileged or destructive work belongs behind Dobby's policy engine.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any


class OSAdapter:
    name = "unknown"

    def environment(self) -> dict[str, Any]:
        return {"os": platform.system(), "release": platform.release(),
                "architecture": platform.machine(), "python": platform.python_version()}

    def find_application(self, name: str) -> dict[str, Any]:
        found = shutil.which(name)
        return {"found": bool(found), "application": name, "executable": found}

    def open_path(self, path: str) -> dict[str, Any]:
        target = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(target):
            return {"success": False, "error_category": "path_not_found", "path": target}
        try:
            if self.name == "windows":
                os.startfile(target)  # type: ignore[attr-defined]
            elif self.name == "macos":
                subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"success": True, "path": target}
        except Exception as exc:
            return {"success": False, "error_category": "open_failed", "error": str(exc), "path": target}

    def launch(self, executable: str, args: list[str] | None = None) -> dict[str, Any]:
        try:
            kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if self.name == "windows":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.Popen([executable] + [str(x) for x in (args or [])], **kwargs)
            return {"success": True, "pid": proc.pid, "executable": executable}
        except Exception as exc:
            return {"success": False, "error_category": "launch_failed", "error": str(exc)}


class WindowsAdapter(OSAdapter):
    name = "windows"


class MacOSAdapter(OSAdapter):
    name = "macos"


class LinuxAdapter(OSAdapter):
    name = "linux"


def get_os_adapter() -> OSAdapter:
    system = platform.system()
    if system == "Windows":
        return WindowsAdapter()
    if system == "Darwin":
        return MacOSAdapter()
    return LinuxAdapter()
