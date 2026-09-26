from __future__ import annotations

from typing import Any

from mcp.models import MCPToolClass
from mcp.permissions import permission_for_tool
from mcp.policy import evaluate_tool_policy
from security.policy import classify


class MCPAdapter:
    def __init__(self, registry=None):
        self.registry = registry

    def route_capability(self, tool_name: str, description: str = "") -> dict[str, Any]:
        permission = permission_for_tool(tool_name, description)
        return {
            "tool": tool_name,
            "classification": permission["classification"],
            "policy_level": permission["policy_level"],
            "requires_confirmation": permission["requires_confirmation"],
            "allow": permission["allow"],
            "source": "mcp",
        }

    def evaluate_execution(self, tool_name: str, parameters: dict[str, Any] | None = None, description: str = "") -> dict[str, Any]:
        decision = evaluate_tool_policy(tool_name, parameters or {}, description)
        return {
            "tool": tool_name,
            "classification": decision.classification,
            "risk_level": decision.risk_level,
            "allowed": decision.allowed,
            "requires_confirmation": decision.requires_confirmation,
            "reason": decision.reason,
        }

    def classify(self, tool_name: str, description: str = "") -> str:
        return permission_for_tool(tool_name, description)["classification"]
