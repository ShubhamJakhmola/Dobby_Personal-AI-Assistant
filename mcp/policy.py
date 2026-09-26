from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp.permissions import permission_for_tool
from security.policy import classify


@dataclass
class MCPPolicyDecision:
    tool_name: str
    classification: str
    risk_level: str
    allowed: bool
    requires_confirmation: bool
    reason: str = ""


def evaluate_tool_policy(tool_name: str, parameters: dict[str, Any] | None = None, description: str = "") -> MCPPolicyDecision:
    permission = permission_for_tool(tool_name, description)
    decision = classify(tool_name, parameters or {})
    allowed = bool(decision.allowed) and bool(permission["allow"])
    requires_confirmation = bool(decision.requires_confirmation or permission["requires_confirmation"])
    risk_level = str(permission["policy_level"])
    classification = permission["classification"]
    reason = decision.reason if decision.reason else "policy evaluation"
    return MCPPolicyDecision(tool_name=tool_name, classification=classification, risk_level=risk_level,
                            allowed=allowed, requires_confirmation=requires_confirmation, reason=reason)
