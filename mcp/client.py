from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import Any

from mcp.models import MCPServerSpec, MCPToolSpec
from security.audit import record


class MCPClient:
    def __init__(self, server: MCPServerSpec):
        self.server = server
        self.process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def start(self) -> dict[str, Any]:
        if not self.server.enabled or not self.server.command:
            return {"status": "DISABLED", "server_id": self.server.server_id}
        try:
            self.process = subprocess.Popen(self.server.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return {"status": "STARTED", "server_id": self.server.server_id, "pid": self.process.pid}
        except Exception as exc:  # pragma: no cover - defensive path
            return {"status": "ERROR", "server_id": self.server.server_id, "error": str(exc)}

    def call_tool(self, tool: MCPToolSpec, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.server.enabled:
            return {"status": "REJECTED", "server_id": self.server.server_id, "tool_id": tool.tool_id, "reason": "server disabled"}
        if self.process is None or self.process.poll() is not None:
            return {"status": "ERROR", "server_id": self.server.server_id, "tool_id": tool.tool_id, "reason": "process unavailable"}
        try:
            payload = json.dumps({"tool": tool.name, "arguments": arguments}).encode("utf-8")
            stdout, stderr = self.process.communicate(input=json.dumps({"tool": tool.name, "arguments": arguments}), timeout=5)
            record(selected_tool="mcp_client", server_id=self.server.server_id, tool_id=tool.tool_id, result=True)
            return {"status": "OK", "server_id": self.server.server_id, "tool_id": tool.tool_id, "output": stdout, "stderr": stderr}
        except Exception as exc:  # pragma: no cover - defensive path
            return {"status": "ERROR", "server_id": self.server.server_id, "tool_id": tool.tool_id, "reason": str(exc)}

    def shutdown(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
