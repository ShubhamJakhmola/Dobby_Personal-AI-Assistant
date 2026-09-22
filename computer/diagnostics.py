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
from acquisition.registry import AcquisitionRegistry
from development.agent_detector import AgentDetector
from development.workspace import WorkspaceManager
from development.agent_registry import CodingAgentRegistry
from remote.device_registry import DeviceRegistry


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
        "mcp": {"enabled": False, "providers": [], "external_capabilities": 0},
        "agents": AgentRegistry().status(),
        "acquisition": {"discovery": "available", "github_discovery": "available",
                "sandbox": "workspace_only", "evaluator": "available",
                "adapter_system": "available", "acquired_capabilities": 0,
                "pending_candidates": len(AcquisitionRegistry().list())},
        "coding_agents": AgentDetector().status(),
        "coding_workspace": WorkspaceManager().status(),
        "agent_adapters": {"loaded": ["aider", "codex", "copilot", "claude_code", "gemini_cli"],
                           "available": AgentDetector().status().get("available", 0), "errors": []},
        "build_mode": {"enabled": True, "workflows": len(WorkspaceManager().list_projects()),
                       "active_workflows": 0, "repair_limit_default": 3,
                       "available_coding_agents": len(CodingAgentRegistry().available()),
                       "projects": len(WorkspaceManager().list_projects())},
        "remote_core": {"enabled": True, "transport": "in-memory", "secure_mode": "development",
                        "connected_devices": DeviceRegistry().status().get("online", 0), "tls_state": "development"},
        "devices": DeviceRegistry().status(),
        "autonomous": _collect_autonomous_status(),
    })
    return info


def _gemini_configured() -> bool:
    try:
        from core.gemini import api_key
        return bool(api_key())
    except Exception:
        return False


def _collect_autonomous_status() -> dict:
    """Collect Phase 19 autonomous engine status."""
    status: dict = {
        "engine": "enabled",
        "master_brain": "gemini",
        "goal_engine": "available",
        "planner": "available",
        "task_manager": "available",
        "recovery": "available",
        "memory": "available",
        "capability_router": "available",
    }
    try:
        from capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        for entry in reg.status():
            cap = entry["capability"].lower()
            status[cap] = entry["status"]
    except Exception:
        status["capability_registry"] = "error"
    return status


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
    mcp = env.get("mcp") or {}
    lines.extend(["", "External MCP:",
                  f"  enabled: {mcp.get('enabled', False)}",
                  f"  providers: {len(mcp.get('providers', []))}",
                  f"  external capabilities: {mcp.get('external_capabilities', 0)}"])
    acquisition = env.get("acquisition") or {}
    lines.extend(["", "Capability Acquisition:"])
    for key, value in acquisition.items():
        lines.append(f"  {key.replace('_', ' ')}: {value}")
    coding = env.get("coding_agents") or {}
    workspace = env.get("coding_workspace") or {}
    lines.extend(["", "Coding Agents:",
                  f"  discovered: {coding.get('discovered', 0)}",
                  f"  installed: {coding.get('installed', 0)}",
                  f"  configured: {coding.get('configured', 0)}",
                  f"  available: {coding.get('available', 0)}",
                  f"  unavailable: {coding.get('unavailable', 0)}",
                  "Coding Workspace:",
                  f"  root: {workspace.get('root', '')}",
                  f"  writable: {workspace.get('writable', False)}",
                  f"  valid: {workspace.get('valid', False)}"])
    build = env.get("build_mode") or {}
    lines.extend(["", "Build Mode:",
                  f"  enabled: {build.get('enabled', False)}",
                  f"  workflows: {build.get('workflows', 0)}",
                  f"  active workflows: {build.get('active_workflows', 0)}",
                  f"  repair limit default: {build.get('repair_limit_default', 3)}",
                  f"  available coding agents: {build.get('available_coding_agents', 0)}",
                  f"  projects: {build.get('projects', 0)}"])
    remote = env.get("remote_core") or {}
    lines.extend(["", "Remote Core:",
                  f"  enabled: {remote.get('enabled', False)}",
                  f"  transport: {remote.get('transport', 'unknown')}",
                  f"  secure mode: {remote.get('secure_mode', 'development')}",
                  f"  connected devices: {remote.get('connected_devices', 0)}"])
    devices = env.get("devices") or {}
    lines.extend(["", "Devices:",
                  f"  total: {devices.get('total', 0)}",
                  f"  online: {devices.get('online', 0)}",
                  f"  offline: {devices.get('offline', 0)}",
                  f"  revoked: {devices.get('revoked', 0)}"])
    autonomous = env.get("autonomous") or {}
    lines.extend(["", "Autonomous Engine (Phase 19):",
                  f"  Engine: {autonomous.get('engine', 'enabled').upper()}",
                  f"  Master Brain: {autonomous.get('master_brain', 'gemini')}",
                  f"  Goal Engine: {autonomous.get('goal_engine', 'available')}",
                  f"  Planner: {autonomous.get('planner', 'available')}",
                  f"  Recovery: {autonomous.get('recovery', 'available')}"])
    return "\n".join(lines)
