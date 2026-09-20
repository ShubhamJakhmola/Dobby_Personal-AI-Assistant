from __future__ import annotations

from typing import Any

from mcp.models import MCPServerSpec, MCPToolSpec


class MCPRegistryState:
    def __init__(self):
        self.servers: dict[str, MCPServerSpec] = {}
        self.tools: dict[str, MCPToolSpec] = {}

    def register_server(self, server: MCPServerSpec) -> None:
        self.servers[server.server_id] = server

    def register_tool(self, tool: MCPToolSpec) -> None:
        self.tools[f"{tool.server_id}:{tool.tool_id}"] = tool

    def server(self, server_id: str) -> MCPServerSpec | None:
        return self.servers.get(server_id)

    def tool(self, server_id: str, tool_id: str) -> MCPToolSpec | None:
        return self.tools.get(f"{server_id}:{tool_id}")

    def list_servers(self) -> list[dict[str, Any]]:
        return [server.as_dict() for server in self.servers.values()]

    def list_tools(self, server_id: str | None = None) -> list[dict[str, Any]]:
        items = list(self.tools.values())
        if server_id is not None:
            items = [item for item in items if item.server_id == server_id]
        return [tool.as_dict() for tool in items]
