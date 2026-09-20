from __future__ import annotations

from typing import Any

from mcp.models import MCPToolClass


def classify_tool(tool_name: str, description: str = "") -> str:
    text = f"{tool_name} {description}".lower()
    if any(token in text for token in ("dangerous", "destructive", "wipe", "destroy", "shutdown", "reboot", "credential", "password", "token", "secret", "account", "payment", "security")):
        return MCPToolClass.SENSITIVE
    if any(token in text for token in ("search", "lookup", "read", "list", "get", "query", "fetch")) and not any(token in text for token in ("create", "update", "send", "delete", "email", "deploy", "write", "modify")):
        return MCPToolClass.READ
    if any(token in text for token in ("create", "write", "update", "modify", "delete", "save", "edit", "patch")):
        return MCPToolClass.WRITE
    if any(token in text for token in ("email", "send", "ticket", "deploy", "cloud", "publish", "webhook", "launch")):
        return MCPToolClass.EXTERNAL_EFFECT
    return MCPToolClass.UNKNOWN


def permission_for_tool(tool_name: str, description: str = "") -> dict[str, Any]:
    classification = classify_tool(tool_name, description)
    if classification == MCPToolClass.READ:
        return {"classification": classification, "policy_level": "L1", "allow": True, "requires_confirmation": False}
    if classification == MCPToolClass.WRITE:
        return {"classification": classification, "policy_level": "L2", "allow": True, "requires_confirmation": False}
    if classification == MCPToolClass.EXTERNAL_EFFECT:
        return {"classification": classification, "policy_level": "L3", "allow": True, "requires_confirmation": True}
    if classification == MCPToolClass.SENSITIVE:
        return {"classification": classification, "policy_level": "L3", "allow": False, "requires_confirmation": True}
    return {"classification": MCPToolClass.UNKNOWN, "policy_level": "L1", "allow": False, "requires_confirmation": True}
