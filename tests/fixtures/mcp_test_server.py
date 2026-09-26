from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def response(request_id, result=None, error=None):
    message = {"jsonrpc": "2.0", "id": request_id}
    message["result" if error is None else "error"] = result if error is None else {"code": -32000, "message": error}
    print(json.dumps(message), flush=True)


def main():
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = request.get("method")
        request_id = request.get("id")
        if method == "initialize":
            response(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "dobby-test-mcp", "version": "1.0"}})
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            response(request_id, {"tools": [
                {"name": "get_status", "description": "Get deterministic status", "inputSchema": {"type": "object", "properties": {}}},
                {"name": "echo", "description": "Echo supplied text", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
                {"name": "calculate", "description": "Calculate two numbers", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}},
                {"name": "create_test_file", "description": "Create a test file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
                {"name": "dangerous_test_action", "description": "Dangerous destructive test action", "inputSchema": {"type": "object", "properties": {}}},
                {"name": "sleep", "description": "Sleep for testing timeout", "inputSchema": {"type": "object", "properties": {"seconds": {"type": "number"}}, "required": ["seconds"]}},
            ]})
        elif method == "tools/call":
            name = request.get("params", {}).get("name")
            arguments = request.get("params", {}).get("arguments", {})
            if name == "get_status": result = {"content": [{"type": "text", "text": "ready"}], "structuredContent": {"status": "ready"}}
            elif name == "echo": result = {"content": [{"type": "text", "text": str(arguments.get("text", ""))}]}
            elif name == "calculate": result = {"content": [{"type": "text", "text": str(arguments.get("a", 0) + arguments.get("b", 0))}], "structuredContent": {"value": arguments.get("a", 0) + arguments.get("b", 0)}}
            elif name == "create_test_file":
                path = Path(arguments.get("path", "")); path.write_text(str(arguments.get("content", "")), encoding="utf-8")
                result = {"content": [{"type": "text", "text": "created"}], "structuredContent": {"path": str(path), "created": True}}
            elif name == "dangerous_test_action": result = {"content": [{"type": "text", "text": "dangerous test action executed"}]}
            elif name == "sleep": time.sleep(float(arguments.get("seconds", 0))); result = {"content": [{"type": "text", "text": "awake"}]}
            else: response(request_id, error="unknown tool"); continue
            response(request_id, result)
        elif request_id is not None:
            response(request_id, error="unknown method")


if __name__ == "__main__":
    main()
