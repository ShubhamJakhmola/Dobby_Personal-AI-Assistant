from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

from mcp.models import MCPServerSpec


@dataclass
class MCPServerRuntime:
    spec: MCPServerSpec
    process: Any | None = None
    started_at: str = ""
    pid: int | None = None
    state: str = "OFFLINE"


class MCPServer:
    def __init__(self, spec: MCPServerSpec):
        self.spec = spec
        self.runtime = MCPServerRuntime(spec)
        self._lock = threading.Lock()

    def start(self) -> dict[str, Any]:
        if not self.spec.enabled or not self.spec.command:
            return {"status": "DISABLED", "server_id": self.spec.server_id}
        try:
            env = os.environ.copy()
            self.runtime.process = subprocess.Popen(self.spec.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            self.runtime.pid = self.runtime.process.pid
            self.runtime.state = "HEALTHY"
            self.runtime.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            return {"status": "STARTED", "server_id": self.spec.server_id, "pid": self.runtime.pid}
        except Exception as exc:  # pragma: no cover - defensive path
            self.runtime.state = "ERROR"
            return {"status": "ERROR", "server_id": self.spec.server_id, "error": str(exc)}

    def stop(self) -> None:
        if self.runtime.process is None or self.runtime.process.poll() is not None:
            self.runtime.state = "OFFLINE"
            return
        self.runtime.process.terminate()
        try:
            self.runtime.process.wait(timeout=5)
        except Exception:
            self.runtime.process.kill()
        self.runtime.state = "OFFLINE"

    def status(self) -> dict[str, Any]:
        return {"server_id": self.spec.server_id, "status": self.runtime.state, "enabled": self.spec.enabled, "trust_state": self.spec.trust_state}
