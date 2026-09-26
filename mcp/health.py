from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MCPHealth:
    server_id: str
    state: str = "OFFLINE"
    last_success: str = ""
    last_error: str = ""
    enabled: bool = False
    trust_state: str = "UNTRUSTED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "server_id": self.server_id,
            "state": self.state,
            "last_success": self.last_success,
            "last_error": self.last_error,
            "enabled": self.enabled,
            "trust_state": self.trust_state,
        }


def health_for_server(server: Any) -> MCPHealth:
    return MCPHealth(server_id=getattr(server, "server_id", "unknown"), state=getattr(server, "status", "OFFLINE"),
                     enabled=getattr(server, "enabled", False), trust_state=getattr(server, "trust_state", "UNTRUSTED"))
