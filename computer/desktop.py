"""Cross-platform desktop control facade.

This is the platform-neutral boundary used by Dobby's higher layers. Optional
backends are detected at runtime so a missing GUI dependency degrades a single
capability instead of breaking startup.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any


def system() -> str:
    return platform.system()


def _pyautogui():
    try:
        import pyautogui
        return pyautogui
    except Exception:
        return None


def mouse(operation: str, **kwargs: Any) -> dict[str, Any]:
    pa = _pyautogui()
    if pa is None:
        return {"success": False, "error_category": "input_backend_unavailable"}
    try:
        if operation == "position":
            p = pa.position(); return {"success": True, "x": p.x, "y": p.y}
        if operation == "move":
            pa.moveTo(float(kwargs["x"]), float(kwargs["y"]), duration=float(kwargs.get("duration", 0))); return {"success": True}
        if operation in {"click", "double_click", "right_click", "middle_click"}:
            button = {"right_click":"right", "middle_click":"middle"}.get(operation, "left")
            pa.click(float(kwargs["x"]) if kwargs.get("x") is not None else None,
                     float(kwargs["y"]) if kwargs.get("y") is not None else None,
                     clicks=2 if operation == "double_click" else 1, button=button)
            return {"success": True}
        return {"success": False, "error_category": "invalid_arguments"}
    except Exception as exc:
        return {"success": False, "error_category": "input_failed", "error": str(exc)}


def keyboard(operation: str, **kwargs: Any) -> dict[str, Any]:
    pa = _pyautogui()
    if pa is None:
        return {"success": False, "error_category": "input_backend_unavailable"}
    try:
        if operation == "type":
            pa.write(str(kwargs.get("text", "")), interval=float(kwargs.get("interval", 0.02))); return {"success": True}
        if operation == "press":
            pa.press(str(kwargs["key"])); return {"success": True}
        if operation == "hotkey":
            pa.hotkey(*[str(k) for k in kwargs.get("keys", [])]); return {"success": True}
        return {"success": False, "error_category": "invalid_arguments"}
    except Exception as exc:
        return {"success": False, "error_category": "keyboard_failed", "error": str(exc)}


def list_windows() -> list[dict[str, Any]] | dict[str, Any]:
    if system() == "Windows":
        try:
            import pygetwindow as gw
            out = []
            for w in gw.getAllWindows():
                title = (w.title or "").strip()
                if title:
                    out.append({"id": str(getattr(w, "_hWnd", "")), "title": title,
                                "left": w.left, "top": w.top, "width": w.width, "height": w.height,
                                "visible": bool(getattr(w, "visible", True))})
            return out
        except Exception as exc:
            return {"available": False, "error_category": "window_backend_unavailable", "error": str(exc)}
    if system() == "Darwin":
        script = 'tell application "System Events" to get name of every application process whose background only is false'
        try:
            p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            if p.returncode == 0:
                return [{"id": None, "title": x.strip(), "application": x.strip()} for x in p.stdout.split(",") if x.strip()]
            return {"available": False, "error_category": "accessibility_unavailable", "error": p.stderr.strip()}
        except Exception as exc:
            return {"available": False, "error_category": "window_backend_unavailable", "error": str(exc)}
    try:
        from computer.linux import windows
        return windows.list_windows()
    except Exception as exc:
        return {"available": False, "error_category": "window_backend_unavailable", "error": str(exc)}


def active_window() -> dict[str, Any]:
    if system() == "Windows":
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return {"available": True, "id": str(hwnd), "title": buf.value or None}
        except Exception as exc:
            return {"available": False, "error": str(exc)}
    if system() == "Darwin":
        script = 'tell application "System Events" to get {name, unix id} of first application process whose frontmost is true'
        try:
            p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                return {"available": True, "title": p.stdout.strip()}
            return {"available": False, "error_category": "accessibility_unavailable", "error": p.stderr.strip()}
        except Exception as exc:
            return {"available": False, "error": str(exc)}
    try:
        from computer.linux import windows
        return windows.active_window()
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def focus_window(window_id: str) -> dict[str, Any]:
    if system() == "Windows":
        try:
            import ctypes
            hwnd = int(str(window_id), 0)
            ok = bool(ctypes.windll.user32.SetForegroundWindow(hwnd))
            return {"success": ok, "window_id": str(window_id), "error_category": None if ok else "focus_failed"}
        except Exception as exc:
            return {"success": False, "error_category": "focus_failed", "error": str(exc)}
    if system() == "Darwin":
        # IDs are not portable across macOS accessibility implementations;
        # focus by application name when supplied as the identifier.
        name = str(window_id).strip()
        script = f'tell application "{name.replace(chr(34), chr(34)+chr(34))}" to activate'
        try:
            p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            return {"success": p.returncode == 0, "error_category": None if p.returncode == 0 else "focus_failed", "error": p.stderr.strip() or None}
        except Exception as exc:
            return {"success": False, "error_category": "focus_failed", "error": str(exc)}
    try:
        from computer.linux import windows
        return windows.focus(str(window_id))
    except Exception as exc:
        return {"success": False, "error_category": "focus_failed", "error": str(exc)}


def screen_info() -> list[dict[str, Any]]:
    try:
        from mss import mss
        with mss() as sct:
            return [{"index": i, "left": m["left"], "top": m["top"], "width": m["width"], "height": m["height"]}
                    for i, m in enumerate(sct.monitors[1:], 1)]
    except Exception:
        return []


def open_path(path: str) -> dict[str, Any]:
    target = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.exists(target):
        return {"success": False, "error_category": "path_not_found", "path": target}
    try:
        if system() == "Windows": os.startfile(target)  # type: ignore[attr-defined]
        elif system() == "Darwin": subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else: subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "path": target}
    except Exception as exc:
        return {"success": False, "error_category": "open_failed", "error": str(exc), "path": target}


def capabilities() -> dict[str, bool]:
    return {"keyboard": _pyautogui() is not None, "mouse": _pyautogui() is not None,
            "windows": bool(list_windows() if system() != "Linux" else True),
            "screen": bool(screen_info())}
