from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from typing import Any

from mcp.discovery import discover_tools
from mcp.models import MCPServerSpec, MCPToolSpec


class MCPStdioClient:
    """Persistent newline-delimited MCP JSON-RPC client for local stdio servers."""

    def __init__(self, server: MCPServerSpec, *, timeout: float = 5.0, max_message: int = 65536):
        self.server = server
        self.timeout = timeout
        self.max_message = max_message
        self.process: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[dict] = queue.Queue()
        self._reader: threading.Thread | None = None
        self._next_id = 0
        self.initialized = False
        self.tools: list[MCPToolSpec] = []
        self.last_error = ""

    def start(self) -> dict:
        if self.server.transport != "stdio":
            return {"status": "UNSUPPORTED", "error": "only stdio transport is enabled"}
        if not self.server.enabled or not self.server.command:
            return {"status": "DISABLED", "server_id": self.server.server_id}
        try:
            allowed_environment = {
                "PATH", "PYTHONIOENCODING", "HOME", "SystemRoot", "WINDIR", "SYSTEMROOT",
                "TEMP", "TMP", "USERPROFILE", "LANG", "LC_ALL", "PYTHONPATH",
            }
            environment = {key: os.environ[key] for key in allowed_environment if os.environ.get(key)}
            environment["PYTHONIOENCODING"] = "utf-8"
            self.process = subprocess.Popen(
                list(self.server.command) + list(self.server.arguments or []),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                bufsize=1,
            )
            self._reader = threading.Thread(target=self._read_loop, daemon=True, name=f"mcp-{self.server.server_id}")
            self._reader.start()
            threading.Thread(target=self._drain_stderr, daemon=True, name=f"mcp-stderr-{self.server.server_id}").start()
            original_timeout = self.timeout
            self.timeout = max(self.timeout, 1.0)
            initialized = self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dobby", "version": "0.1"},
            })
            if "error" in initialized:
                return self._fail("initialize failed")
            self._notify("notifications/initialized", {})
            self.initialized = True
            self.timeout = original_timeout
            self.server.status = "AVAILABLE"
            return {"status": "AVAILABLE", "server_id": self.server.server_id, "server_info": initialized.get("result", {}).get("serverInfo", {})}
        except Exception as exc:
            return self._fail(str(exc))

    def _read_loop(self):
        assert self.process and self.process.stdout
        try:
            for line in self.process.stdout:
                if len(line.encode("utf-8")) > self.max_message:
                    self.last_error = "MCP message exceeded maximum size"
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    self.last_error = "malformed MCP JSON"
                    continue
                if isinstance(message, dict) and "id" in message:
                    self._responses.put(message)
        except (OSError, ValueError) as exc:
            self.last_error = str(exc)

    def _drain_stderr(self):
        if not self.process or not self.process.stderr:
            return
        try:
            for _ in self.process.stderr:
                pass
        except (OSError, ValueError):
            pass

    def _send(self, message: dict):
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            raise RuntimeError("MCP process is not running")
        encoded = json.dumps(message, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > self.max_message:
            raise ValueError("MCP request exceeds maximum size")
        self.process.stdin.write(encoded + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        request_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                response = self._responses.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if response.get("id") == request_id:
                return response
        raise TimeoutError(f"MCP request timed out: {method}")

    def _notify(self, method: str, params: dict):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def list_tools(self) -> list[MCPToolSpec]:
        if not self.initialized:
            raise RuntimeError("MCP client is not initialized")
        response = self._request("tools/list", {})
        if "error" in response:
            raise RuntimeError(str(response["error"]))
        self.tools = discover_tools(self.server.server_id, response.get("result", {}).get("tools", []))
        self.server.capabilities = [tool.name for tool in self.tools]
        return self.tools

    def call_tool(self, tool: MCPToolSpec | str, arguments: dict[str, Any]) -> dict:
        name = tool.name if isinstance(tool, MCPToolSpec) else str(tool)
        if not self.initialized or not any(item.name == name for item in self.tools):
            return {"status": "REJECTED", "reason": "tool is not discovered"}
        try:
            response = self._request("tools/call", {"name": name, "arguments": arguments})
            if "error" in response:
                return {"status": "ERROR", "error": response["error"]}
            return {"status": "COMPLETED", "result": response.get("result", {})}
        except TimeoutError as exc:
            return {"status": "TIMEOUT", "error": str(exc)}
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc)}

    def _fail(self, reason: str) -> dict:
        self.last_error = reason
        self.server.status = "ERROR"
        return {"status": "ERROR", "server_id": self.server.server_id, "error": reason}

    def shutdown(self):
        if self.process is None:
            return
        if self.process.stdin and self.process.poll() is None:
            try:
                self._notify("notifications/cancelled", {})
            except Exception:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        self.process = None
        self.initialized = False
        self.server.status = "UNAVAILABLE"
