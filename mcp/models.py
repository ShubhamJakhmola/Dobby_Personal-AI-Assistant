from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class MCPServerState:
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


class MCPToolClass:
    READ = "READ"
    WRITE = "WRITE"
    EXTERNAL_EFFECT = "EXTERNAL_EFFECT"
    SENSITIVE = "SENSITIVE"
    UNKNOWN = "UNKNOWN"


class MCPTrustState:
    UNTRUSTED = "UNTRUSTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    TRUSTED = "TRUSTED"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


@dataclass
class MCPServerSpec:
    server_id: str
    name: str
    description: str = ""
    transport: str = "stdio"
    endpoint: str = ""
    command: list[str] | None = None
    arguments: list[str] | None = None
    environment_refs: list[str] | None = None
    enabled: bool = False
    trust_state: str = MCPTrustState.UNTRUSTED
    status: str = MCPServerState.NOT_CONFIGURED
    discovered_at: str = ""
    capabilities: list[str] = field(default_factory=list)
    version: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "description": self.description,
            "transport": self.transport,
            "endpoint": self.endpoint,
            "command": self.command or [],
            "arguments": self.arguments or [],
            "environment_refs": self.environment_refs or [],
            "enabled": self.enabled,
            "trust_state": self.trust_state,
            "status": self.status,
            "discovered_at": self.discovered_at,
            "capabilities": list(self.capabilities),
            "version": self.version,
        }


@dataclass
class MCPToolSpec:
    server_id: str
    tool_id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    declared_annotations: dict[str, Any] | None = None
    capability_class: str = MCPToolClass.UNKNOWN
    risk_level: str = "L1"
    enabled: bool = False
    verified: bool = False
    discovered_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema or {},
            "output_schema": self.output_schema or {},
            "declared_annotations": self.declared_annotations or {},
            "capability_class": self.capability_class,
            "risk_level": self.risk_level,
            "enabled": self.enabled,
            "verified": self.verified,
            "discovered_at": self.discovered_at,
        }
