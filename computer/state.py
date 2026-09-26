"""Current-world state used by Dobby's computer-use loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any
import platform
import subprocess

@dataclass
class ComputerState:
    active_application: str | None = None
    active_window: str | None = None
    active_browser: str | None = None
    active_url: str | None = None
    active_tab: str | None = None
    media_title: str | None = None
    media_state: str | None = None
    media_volume: int | None = None
    ad_detected: bool | None = None
    last_action: dict[str, Any] | None = None
    last_observation: dict[str, Any] | None = None
    task_id: str | None = None
    task_goal: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    focused_process: str | None = None
    browser_session: str | None = None
    browser_tab_count: int | None = None
    task_status: str | None = None

    def update(self, **values: Any) -> None:
        for key, value in values.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)

    def snapshot(self) -> dict[str, Any]:
        return {
            "active_application": self.active_application,
            "active_window": self.active_window,
            "active_browser": self.active_browser,
            "active_url": self.active_url,
            "active_tab": self.active_tab,
            "media_title": self.media_title,
            "media_state": self.media_state,
            "media_volume": self.media_volume,
            "ad_detected": self.ad_detected,
            "last_action": self.last_action,
            "last_observation": self.last_observation,
            "task_id": self.task_id,
            "task_goal": self.task_goal,
            "metadata": dict(self.metadata),
            "focused_process": self.focused_process,
            "browser_session": self.browser_session,
            "browser_tab_count": self.browser_tab_count,
            "task_status": self.task_status,
        }

_STATE = ComputerState()
_LOCK = RLock()

def get_state() -> ComputerState:
    return _STATE

def update_state(**values: Any) -> dict[str, Any]:
    with _LOCK:
        _STATE.update(**values)
        return _STATE.snapshot()

def reset_state() -> None:
    global _STATE
    with _LOCK:
        _STATE = ComputerState()

def observe_desktop() -> dict[str, Any]:
    """Cheap local observation. It never calls an LLM or the network."""
    result: dict[str, Any] = {"platform": platform.system()}
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            result["active_window"] = buf.value or None
        elif system == "Linux":
            p = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                result["active_window"] = p.stdout.strip() or None
        elif system == "Darwin":
            p = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'], capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                result["active_application"] = p.stdout.strip() or None
    except Exception as exc:
        result["observation_error"] = str(exc)
    update_state(last_observation=result, active_window=result.get("active_window"), active_application=result.get("active_application"))
    return get_state().snapshot()
