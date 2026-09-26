"""Safe first-pass diagnostics for common local-system problems."""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path

import psutil


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _diagnose_system() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))
    checks = {
        "os": platform.platform(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": vm.percent,
        "ram_available_gb": round(vm.available / 2**30, 2),
        "disk_free_gb": round(disk.free / 2**30, 2),
        "process_count": len(psutil.pids()),
        "network_interfaces": list(psutil.net_if_addrs().keys()),
    }
    findings = []
    if vm.percent >= 90:
        findings.append("RAM usage is critically high; inspect top RAM consumers before terminating anything.")
    if disk.percent >= 90:
        findings.append("The system disk is over 90% full; identify large files before deleting anything.")
    if not findings:
        findings.append("No critical resource threshold was detected by the basic read-only checks.")
    return {"checks": checks, "findings": findings}


def _diagnose_network() -> dict:
    result = {"dns": False, "internet": False, "default_gateway": None, "findings": []}
    try:
        socket.gethostbyname("example.com")
        result["dns"] = True
    except Exception as exc:
        result["dns_error"] = str(exc)
    try:
        result["internet"] = bool(socket.create_connection(("1.1.1.1", 443), timeout=3))
    except Exception as exc:
        result["internet_error"] = str(exc)
    if not result["dns"]:
        result["findings"].append("DNS resolution failed.")
    elif not result["internet"]:
        result["findings"].append("DNS works but an outbound connectivity test failed.")
    else:
        result["findings"].append("Basic DNS and outbound connectivity checks passed.")
    return result


def troubleshoot(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "diagnose")).lower().strip()
    target = str(params.get("target", "system")).lower().strip()
    if operation == "diagnose":
        if target == "network":
            result = _diagnose_network()
        elif target == "system":
            result = _diagnose_system()
        elif target == "disk":
            disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))
            result = {"total_gb": round(disk.total / 2**30, 2), "used_gb": round(disk.used / 2**30, 2), "free_gb": round(disk.free / 2**30, 2), "percent": disk.percent}
        elif target == "display":
            result = {"platform": platform.system(), "pyautogui": _command_exists("python"), "display_env": os.environ.get("DISPLAY"), "wayland": os.environ.get("WAYLAND_DISPLAY")}
        else:
            result = {"success": False, "error": f"Unknown diagnostic target: {target}"}
        return json.dumps({"success": True, "operation": operation, "target": target, "result": result}, ensure_ascii=True)
    if operation == "plan_fix":
        diagnosis = troubleshoot({"operation": "diagnose", "target": target})
        return json.dumps({"success": True, "mode": "plan_only", "diagnosis": json.loads(diagnosis), "next_step": "Dobby must inspect the proposed remediation and obtain confirmation before any destructive or privileged change."}, ensure_ascii=True)
    return json.dumps({"success": False, "error": "Supported operations: diagnose, plan_fix."})


TOOL = {
    "name": "troubleshoot",
    "description": "Perform read-only diagnostics and produce a safe remediation plan for system, network, disk, or display problems. It does not make destructive or privileged changes.",
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING"},
        "target": {"type": "STRING"},
    }, "required": ["operation"]},
    "handler": troubleshoot,
    "risk_level": "L0",
    "reversible": True,
    "supports_verification": True,
}
