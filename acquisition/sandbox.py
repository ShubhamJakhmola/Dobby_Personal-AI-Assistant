from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


class Sandbox:
    def __init__(self, root=None):
        self.root = Path(root or Path.home() / ".dobby" / "acquisition" / "sandbox")

    def workspace(self, candidate_id: str) -> Path:
        path = self.root / candidate_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run(self, command: list[str], workspace: Path, timeout: float = 30, network: bool = False) -> dict:
        allowed_environment = {"PATH", "PYTHONIOENCODING", "HOME", "SystemRoot", "WINDIR",
                       "TEMP", "TMP", "USERPROFILE", "SYSTEMROOT"}
        env = {key: os.environ[key] for key in allowed_environment if os.environ.get(key)}
        env.update({"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "HOME": str(workspace)})
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True,
                                    timeout=timeout, check=False)
            return {"success": result.returncode == 0, "status": "completed" if result.returncode == 0 else "failed",
                    "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                    "duration": time.monotonic() - started, "sandbox_strength": "workspace_only",
                    "network": "enabled" if network else "disabled"}
        except subprocess.TimeoutExpired as exc:
            return {"success": False, "status": "timeout", "error": str(exc), "sandbox_strength": "workspace_only"}