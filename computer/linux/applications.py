from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import psutil


def discover() -> list[dict]:
    apps: dict[str, dict] = {}
    for directory in (Path.home() / ".local/share/applications", Path("/usr/share/applications")):
        if not directory.exists():
            continue
        for desktop in directory.glob("*.desktop"):
            try:
                values = {}
                for line in desktop.read_text(encoding="utf-8", errors="replace").splitlines():
                    key, separator, value = line.partition("=")
                    if separator:
                        values[key] = value
                name = values.get("Name")
                command = values.get("Exec", "").split(" %", 1)[0].strip()
                if name and command:
                    apps[name.lower()] = {"name": name, "command": command, "desktop_file": str(desktop)}
            except OSError:
                continue
    return list(apps.values())


def find(application: str) -> dict | None:
    query = application.lower().strip()
    executable = shutil.which(application) or shutil.which(query.replace(" ", "-"))
    if executable:
        return {"name": application, "executable": executable, "source": "PATH"}
    return next((item for item in discover() if query in item["name"].lower()), None)


def is_running(application: str) -> list[int]:
    query = application.lower()
    matches = []
    for process in psutil.process_iter(["name", "cmdline"]):
        try:
            haystack = ((process.info.get("name") or "") + " " + " ".join(process.info.get("cmdline") or [])).lower()
            if query in haystack:
                matches.append(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matches


def launch(application: str, wait: float = 1.0) -> dict:
    found = find(application)
    if not found:
        return {"success": False, "error_category": "application_not_found", "error": application}
    command = found["executable"] if found.get("executable") else found["command"].split()
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(max(0.0, min(float(wait), 5.0)))
        pids = is_running(application) or ([process.pid] if psutil.pid_exists(process.pid) else [])
        return {"success": bool(pids), "application": application, "pid": process.pid, "pids": pids,
                "running": bool(pids), "verified": bool(pids)}
    except OSError as exc:
        return {"success": False, "error_category": "application_launch_failed", "error": str(exc)}


def close(application: str, timeout: float = 5.0) -> dict:
    pids = is_running(application)
    results = []
    for pid in pids:
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=timeout)
            results.append({"pid": pid, "stopped": not process.is_running()})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as exc:
            results.append({"pid": pid, "stopped": False, "error": str(exc)})
    stopped = not is_running(application)
    return {"success": stopped, "application": application, "pids": pids, "stopped": stopped,
            "verified": stopped, "results": results}