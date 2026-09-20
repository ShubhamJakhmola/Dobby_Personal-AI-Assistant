from __future__ import annotations

from typing import Any

from mcp.models import MCPServerSpec, MCPToolSpec
from mcp.permissions import permission_for_tool


def discover_server(server_id: str, name: str, *, transport: str = "stdio", description: str = "") -> MCPServerSpec:
    return MCPServerSpec(
        server_id=server_id,
        name=name,
        description=description,
        transport=transport,
        enabled=False,
        status="NOT_CONFIGURED",
        discovered_at="unknown",
        capabilities=[],
    )


def discover_tools(server_id: str, tools: list[dict[str, Any]]) -> list[MCPToolSpec]:
    result: list[MCPToolSpec] = []
    for tool in tools:
        name = str(tool.get("name") or tool.get("tool_id") or "unknown")
        description = str(tool.get("description") or "")
        permission = permission_for_tool(name, description)
        result.append(MCPToolSpec(
            server_id=server_id,
            tool_id=str(tool.get("tool_id") or name),
            name=name,
            description=description,
            input_schema=tool.get("input_schema") or {},
            output_schema=tool.get("output_schema") or {},
            declared_annotations=tool.get("annotations") or {},
            capability_class=permission["classification"],
            risk_level=permission["policy_level"],
            enabled=False,
            verified=False,
            discovered_at="unknown",
        ))
    return result
