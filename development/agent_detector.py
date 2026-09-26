from __future__ import annotations

from development.adapters import DEFAULT_ADAPTERS
from development.models import CodingAgentInfo


class AgentDetector:
    def __init__(self, adapter_classes=None):
        self.adapter_classes = adapter_classes or DEFAULT_ADAPTERS

    def detect(self) -> list[CodingAgentInfo]:
        found = []
        for adapter_class in self.adapter_classes:
            try:
                found.append(adapter_class().detect())
            except Exception as exc:
                adapter = adapter_class()
                info = adapter.detect()
                info.errors.append(str(exc))
                found.append(info)
        return found

    def status(self) -> dict:
        agents = [item.as_dict() for item in self.detect()]
        return {
            "discovered": len(agents),
            "installed": sum(1 for item in agents if item["installed"]),
            "configured": sum(1 for item in agents if item["configured"]),
            "available": sum(1 for item in agents if item["available"]),
            "unavailable": sum(1 for item in agents if not item["available"]),
            "agents": agents,
        }
