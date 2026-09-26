import unittest

from mcp.discovery import discover_server, discover_tools
from mcp.models import MCPServerSpec, MCPToolSpec, MCPServerState, MCPToolClass
from mcp.permissions import permission_for_tool
from mcp.policy import evaluate_tool_policy
from mcp.provider import ControlledMCPProvider, MCPRegistry
from security.policy import classify


class PhaseSixteenTests(unittest.TestCase):
    def test_mcp_provider_registration_and_capabilities(self):
        provider = ControlledMCPProvider("demo", {"filesystem.list": {"description": "List files", "kind": "read"}, "terminal.execute": {"description": "Run command", "kind": "command"}})
        self.assertEqual(provider.name, "demo")
        self.assertIn("filesystem.list", provider.capabilities())
        self.assertTrue(provider.supports("filesystem.list"))

    def test_mcp_provider_requires_policy_gate_for_terminal(self):
        provider = ControlledMCPProvider("demo", {"terminal.execute": {"description": "Run command", "kind": "command"}})
        decision = classify("terminal_execute", {"command": ["printf", "ok"]})
        self.assertTrue(provider.policy_gate("terminal.execute", {"command": ["printf", "ok"]}, decision))
        high = classify("terminal_execute", {"command": ["sudo", "id"]})
        self.assertFalse(provider.policy_gate("terminal.execute", {"command": ["sudo", "id"]}, high))

    def test_mcp_registry_and_external_capability_request(self):
        registry = MCPRegistry()
        provider = ControlledMCPProvider("demo", {"filesystem.list": {"description": "List files", "kind": "read"}})
        registry.register(provider)
        req = registry.request("filesystem.list", {"path": "."})
        self.assertEqual(req["provider"], "demo")
        self.assertEqual(req["capability"], "filesystem.list")

    def test_mcp_cannot_bypass_local_action_policy(self):
        registry = MCPRegistry()
        provider = ControlledMCPProvider("demo", {"terminal.execute": {"description": "Run shell", "kind": "command"}})
        registry.register(provider)
        result = registry.execute("terminal.execute", {"command": ["sudo", "systemctl", "restart", "nginx"]})
        self.assertEqual(result["status"], "BLOCKED")

    def test_server_model_and_configuration_defaults(self):
        server = MCPServerSpec(server_id="docs", name="Docs", transport="stdio", enabled=False)
        self.assertEqual(server.status, MCPServerState.NOT_CONFIGURED)
        self.assertFalse(server.enabled)
        self.assertIn("server_id", server.as_dict())

    def test_tool_classification_and_policy_integration(self):
        read_perm = permission_for_tool("search_docs", "search documentation")
        self.assertEqual(read_perm["classification"], MCPToolClass.READ)
        self.assertEqual(read_perm["policy_level"], "L1")

        write_perm = permission_for_tool("create_secrets", "create credentials file")
        self.assertEqual(write_perm["classification"], MCPToolClass.SENSITIVE)

        external_perm = permission_for_tool("send_email", "send email")
        self.assertEqual(external_perm["classification"], MCPToolClass.EXTERNAL_EFFECT)
        self.assertTrue(external_perm["requires_confirmation"])

        policy = evaluate_tool_policy("dangerous_test_action", {"command": ["sudo", "id"]}, "dangerous action")
        self.assertEqual(policy.classification, MCPToolClass.SENSITIVE)
        self.assertTrue(policy.requires_confirmation)

    def test_discovery_and_tool_schema_extraction(self):
        server = discover_server("docs", "Docs", description="Documentation server")
        tools = discover_tools("docs", [{"tool_id": "search_docs", "name": "search_docs", "description": "search documentation", "input_schema": {"type": "object"}}])
        self.assertEqual(server.server_id, "docs")
        self.assertEqual(tools[0].tool_id, "search_docs")
        self.assertEqual(tools[0].capability_class, MCPToolClass.READ)

    def test_server_revocation_and_disabled_rejection(self):
        registry = MCPRegistry()
        provider = ControlledMCPProvider("demo", {"filesystem.list": {"description": "List files", "kind": "read"}})
        provider.disabled = True
        registry.register(provider)
        result = registry.execute("filesystem.list", {"path": "."})
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
