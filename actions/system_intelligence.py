"""Read-only system intelligence plus guarded process/resource cleanup."""
from __future__ import annotations

import json
import os
import platform
import shutil
import time
from pathlib import Path

import psutil

_PROTECTED = {
    "system", "system idle process", "idle", "registry", "wininit", "winlogon",
    "services.exe", "lsass.exe", "smss.exe", "csrss.exe", "svchost.exe",
    "launchd", "kernel_task", "systemd", "init", "kthreadd", "dbus-daemon",
}


def _gpu_info() -> dict | None:
    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        devices = []
        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode(errors="replace")
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            devices.append({"name": str(name), "memory_total_gb": round(mem.total / 2**30, 2), "memory_used_gb": round(mem.used / 2**30, 2), "utilization_percent": int(util.gpu)})
        return {"vendor": "NVIDIA", "devices": devices}
    except Exception:
        return None


def _specs() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))
    return {
        "os": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "cpu_logical": psutil.cpu_count(logical=True),
        "cpu_physical": psutil.cpu_count(logical=False),
        "ram_total_gb": round(vm.total / 2**30, 2),
        "disk_root_total_gb": round(disk.total / 2**30, 2),
        "disk_root_free_gb": round(disk.free / 2**30, 2),
        "gpu": _gpu_info(),
    }


def _top_processes(limit: int = 15) -> list[dict]:
    rows = []
    for proc in psutil.process_iter(["pid", "name", "username", "status", "memory_info", "create_time"]):
        try:
            info = proc.info
            rss = info.get("memory_info").rss if info.get("memory_info") else 0
            rows.append({
                "pid": proc.pid,
                "name": info.get("name") or "",
                "user": info.get("username"),
                "status": info.get("status"),
                "ram_mb": round(rss / 2**20, 1),
                "age_hours": round(max(0, time.time() - (info.get("create_time") or time.time())) / 3600, 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(rows, key=lambda x: x["ram_mb"], reverse=True)[:max(1, min(limit, 100))]


def _cleanup_candidates(min_ram_mb: float = 300) -> list[dict]:
    candidates = []
    current = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "username", "status", "memory_info", "create_time"]):
        try:
            info = proc.info
            pid = int(info["pid"])
            name = (info.get("name") or "").strip()
            rss = info.get("memory_info").rss if info.get("memory_info") else 0
            if pid == current or name.lower() in _PROTECTED or rss < min_ram_mb * 2**20:
                continue
            candidates.append({
                "pid": pid,
                "name": name,
                "user": info.get("username"),
                "status": info.get("status"),
                "ram_mb": round(rss / 2**20, 1),
                "age_hours": round(max(0, time.time() - (info.get("create_time") or time.time())) / 3600, 1),
                "reason": "large RAM consumer; not classified as a protected OS process",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(candidates, key=lambda x: x["ram_mb"], reverse=True)[:50]


def system_intelligence(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "health")).lower().strip()
    if operation == "specs":
        return json.dumps(_specs(), ensure_ascii=True)
    if operation in {"top_resources", "top_processes"}:
        return json.dumps({"processes": _top_processes(int(params.get("limit", 15)))}, ensure_ascii=True)
    if operation in {"cleanup_candidates", "analyze_cleanup"}:
        return json.dumps({"warning": "High RAM use does not prove a process is unused.", "candidates": _cleanup_candidates(float(params.get("min_ram_mb", 300)))}, ensure_ascii=True)
    if operation == "safe_stop":
        raw = params.get("pids", [])
        if not isinstance(raw, list) or not raw or not all(str(x).isdigit() for x in raw):
            return json.dumps({"success": False, "error_category": "invalid_arguments", "error": "safe_stop requires an explicit list of process PIDs."})
        current = os.getpid()
        results = []
        for raw_pid in raw:
            pid = int(raw_pid)
            if pid == current:
                results.append({"pid": pid, "stopped": False, "reason": "Dobby protects its own process"})
                continue
            try:
                proc = psutil.Process(pid)
                name = proc.name()
                if name.lower() in _PROTECTED:
                    results.append({"pid": pid, "name": name, "stopped": False, "reason": "protected system process"})
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    results.append({"pid": pid, "name": name, "stopped": False, "reason": "did not exit after graceful terminate"})
                    continue
                results.append({"pid": pid, "name": name, "stopped": not proc.is_running()})
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                results.append({"pid": pid, "stopped": False, "reason": str(exc)})
        return json.dumps({"success": all(x.get("stopped") or "reason" in x for x in results), "operation": "safe_stop", "results": results}, ensure_ascii=True)
    if operation == "health":
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))
        return json.dumps({
            "cpu_percent": psutil.cpu_percent(interval=0.15),
            "ram_percent": vm.percent,
            "ram_available_gb": round(vm.available / 2**30, 2),
            "disk_free_gb": round(disk.free / 2**30, 2),
            "process_count": len(psutil.pids()),
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1),
        }, ensure_ascii=True)
    return json.dumps({"success": False, "error": "Supported operations: specs, health, top_resources, cleanup_candidates, safe_stop."})


TOOL = {
    "name": "system_intelligence",
    "description": "Inspect system specifications, health, RAM-heavy processes, and safe cleanup candidates. Analysis is read-only; it never assumes a process is unused just because it uses RAM.",
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING"},
        "limit": {"type": "NUMBER"},
        "min_ram_mb": {"type": "NUMBER"},
        "pids": {"type": "ARRAY", "items": {"type": "INTEGER"}},
    }, "required": ["operation"]},
    "handler": system_intelligence,
    "risk_level": "L0",
    "reversible": True,
    "supports_verification": True,
}
