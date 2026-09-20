from __future__ import annotations

import importlib.util
import os
import shutil

from computer.linux import applications, clipboard, keyboard, mouse, screen, windows
from computer.platform import environment
from memory.storage import memory_root
from memory.task_state import TaskStateStore
from brain.defaults import create_registry
from brain.budgets import BudgetManager
from brain.usage import UsageTracker
from agents.registry import AgentRegistry


def collect_environment() -> dict:
    info = environment()
    linux = info["os"] == "Linux"
    info.update({
        "screen_capture": {"status": "available" if screen.detect_backends() else "unavailable", "backends": screen.detect_backends()},
        "monitors": [item.as_dict() for item in screen.list_monitors()] if linux and screen.detect_backends() else [],
        "mouse": "available" if linux and mouse.pyautogui is not None else "unavailable",
        "keyboard": "available" if linux and keyboard.pyautogui is not None else "unavailable",
        "clipboard": "available" if linux and clipboard.pyperclip is not None else "unavailable",
        "window_manager": "available" if linux and windows._tool() else "unavailable",
        "application_discovery": "available" if linux and applications.discover() else "unavailable",
        "browser": "available" if importlib.util.find_spec("playwright") else "optional/unavailable",
        "playwright": bool(importlib.util.find_spec("playwright")),
        "gemini": "configured" if _gemini_configured() else "missing",
        "memory": {
            "current_context": "available",
            "conversation_storage": "available",
            "long_term_memory": "available",
            "retrieval": "available",
            "task_state": "available" if TaskStateStore().status()["available"] else "unavailable",
            "project_context": "available",
            "path": str(memory_root()),
        },
        "brain": {
            "master_provider": "gemini",
            "providers": create_registry().list(),
            "usage_tracking": "available",
            "budget_manager": "available",
        },
        "agents": AgentRegistry().status(),
    })
    return info


def _gemini_configured() -> bool:
    try:
        from core.gemini import api_key
        return bool(api_key())
    except Exception:
        return False


def run_live_validation() -> dict:
    """Run safe observation checks; never stores a screenshot or clicks/types."""
    result = {"environment": collect_environment(), "screen": {}, "windows": {}, "applications": {},
              "input": {"status": "not_run", "reason": "live validation does not type or click automatically"}}
    if result["environment"]["os"] != "Linux":
        result["status"] = "unavailable_on_current_host"
        return result
    primary = screen.get_primary_monitor()
    if primary is None:
        result["screen"] = {"status": "unavailable", "error_category": "monitor_not_found"}
    else:
        frame = screen.capture_monitor(primary.index)
        result["screen"] = {"status": "live_verified" if frame.success else "failed",
                             "primary_monitor": primary.as_dict(), "frame": frame.as_dict()}
    result["windows"] = {"status": "live_verified", "active": windows.active_window(), "windows": windows.list_windows()}
    result["applications"] = {"status": "live_verified", "count": len(applications.discover())}
    result["status"] = "live_verified"
    return result


def format_report(data: dict) -> str:
    env = data
    lines = ["Dobby Linux Diagnostics", "", f"OS: {env.get('os')}", f"Kernel: {env.get('kernel')}",
             f"Python: {env.get('python')}", f"Desktop: {env.get('desktop')}",
             f"Display Server: {env.get('display_server')}", f"Monitors: {len(env.get('monitors', []))} detected", "",
             "Screen Capture:", f"  Status: {env.get('screen_capture', {}).get('status', 'unavailable').upper()}",
             f"  Backends: {', '.join(env.get('screen_capture', {}).get('backends', [])) or 'none'}", "",
             f"Mouse: {str(env.get('mouse', 'unavailable')).upper()}",
             f"Keyboard: {str(env.get('keyboard', 'unavailable')).upper()}",
             f"Clipboard: {str(env.get('clipboard', 'unavailable')).upper()}",
             f"Window Manager: {str(env.get('window_manager', 'unavailable')).upper()}",
             f"Application Discovery: {str(env.get('application_discovery', 'unavailable')).upper()}",
             f"Browser: {str(env.get('browser', 'unavailable')).upper()}",
             f"Gemini: {str(env.get('gemini', 'missing')).upper()}", "",
             "Memory:"]
    for key, value in (env.get("memory") or {}).items():
        if key != "path":
            lines.append(f"  {key.replace('_', ' ')}: {value}")
    brain = env.get("brain") or {}
    lines.extend(["", "Brain:", f"  master provider: {brain.get('master_provider', 'gemini')}"])
    for profile in brain.get("providers", []):
        lines.append(f"  {profile.get('provider_id')}: {'available' if profile.get('available') else 'unavailable/unconfigured'}")
    lines.extend(["  usage tracking: available", "  budget manager: available"])
    return "\n".join(lines)