from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp.discovery import discover_tools
from mcp.models import MCPServerSpec, MCPToolClass
from mcp.policy import evaluate_tool_policy
from mcp.stdio import MCPStdioClient


class PhaseSeventeenTests(unittest.TestCase):
    def make_server(self, timeout=2):
        fixture = Path(__file__).parent / "fixtures" / "mcp_test_server.py"
        return MCPServerSpec(server_id="phase17", name="Phase 17 Test MCP", transport="stdio",
                             command=[sys.executable, str(fixture)], arguments=[], enabled=True, trust_state="TRUSTED", status="CONFIGURED")

    def test_real_stdio_initialize_discovery_and_cleanup(self):
        client = MCPStdioClient(self.make_server(), timeout=2)
        try:
            started = client.start()
            self.assertEqual(started["status"], "AVAILABLE")
            tools = client.list_tools()
            self.assertIn("get_status", [tool.name for tool in tools])
        finally:
            client.shutdown()
        self.assertIsNone(client.process)

    def test_real_tool_execution_echo_and_calculate(self):
        client = MCPStdioClient(self.make_server())
        try:
            client.start(); client.list_tools()
            echo = client.call_tool("echo", {"text": "hello"})
            calc = client.call_tool("calculate", {"a": 2, "b": 3})
            self.assertEqual(echo["status"], "COMPLETED")
            self.assertEqual(calc["result"]["structuredContent"]["value"], 5)
        finally:
            client.shutdown()

    def test_schema_discovery_and_unknown_tool_rejection(self):
        client = MCPStdioClient(self.make_server())
        try:
            client.start(); tools = client.list_tools()
            echo = next(tool for tool in tools if tool.name == "echo")
            self.assertIn("required", echo.input_schema)
            result = client.call_tool("unknown_tool", {})
            self.assertEqual(result["status"], "REJECTED")
        finally:
            client.shutdown()

    def test_l3_policy_blocks_dangerous_tool(self):
        decision = evaluate_tool_policy("dangerous_test_action", {}, "Dangerous destructive test action")
        self.assertEqual(decision.classification, MCPToolClass.SENSITIVE)
        self.assertTrue(decision.requires_confirmation)

    def test_timeout_and_restart(self):
        client = MCPStdioClient(self.make_server(), timeout=0.05)
        try:
            client.start(); client.list_tools()
            result = client.call_tool("sleep", {"seconds": 0.5})
            self.assertEqual(result["status"], "TIMEOUT")
        finally:
            client.shutdown()
        restarted = MCPStdioClient(self.make_server())
        try:
            self.assertEqual(restarted.start()["status"], "AVAILABLE")
            self.assertTrue(restarted.list_tools())
        finally:
            restarted.shutdown()


if __name__ == "__main__":
    unittest.main()
