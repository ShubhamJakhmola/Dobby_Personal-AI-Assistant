from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClientRuntime:
    name: str = "dobby-client"
    platform: str = "linux"
    status: str = "ready"
    capabilities: list[str] = field(default_factory=lambda: ["filesystem", "terminal", "process"])
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"name": self.name, "platform": self.platform, "status": self.status, "capabilities": self.capabilities}

    def status_report(self) -> dict:
        return self.as_dict()
