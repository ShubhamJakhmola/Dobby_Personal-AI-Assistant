from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MCPTransportSpec:
    transport: str = "stdio"
    endpoint: str = ""
    timeout: float = 5.0
    max_stdout: int = 4096
    max_stderr: int = 4096
    max_payload: int = 65536
    network_enabled: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "endpoint": self.endpoint,
            "timeout": self.timeout,
            "max_stdout": self.max_stdout,
            "max_stderr": self.max_stderr,
            "max_payload": self.max_payload,
            "network_enabled": self.network_enabled,
        }
