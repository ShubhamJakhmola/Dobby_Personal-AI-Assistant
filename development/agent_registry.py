from __future__ import annotations

from development.agent_detector import AgentDetector
from development.models import CodingAgentInfo


class CodingAgentRegistry:
    def __init__(self, detector: AgentDetector | None = None):
        self.detector = detector or AgentDetector()
        self._agents: dict[str, CodingAgentInfo] = {}

    def refresh(self) -> list[dict]:
        self._agents = {agent.id: agent for agent in self.detector.detect()}
        return self.list()

    def list(self) -> list[dict]:
        if not self._agents:
            self.refresh()
        return [agent.as_dict() for agent in self._agents.values()]

    def get(self, agent_id: str) -> dict | None:
        if not self._agents:
            self.refresh()
        agent = self._agents.get(agent_id)
        return agent.as_dict() if agent else None

    def available(self) -> list[dict]:
        return [agent for agent in self.list() if agent.get("available")]

    def capabilities(self) -> list[dict]:
        return [coding_agent_capability(agent) for agent in self.list() if agent.get("available")]

    def status(self) -> dict:
        agents = self.list()
        return {"available": bool([item for item in agents if item.get("available")]),
                "count": len(agents),
                "available_count": sum(1 for item in agents if item.get("available")),
                "agents": agents}


def coding_agent_capability(agent: dict) -> dict:
    return {
        "name": f"coding_agent.{agent['id']}",
        "provider": agent.get("provider", ""),
        "executable": agent.get("executable", ""),
        "version": agent.get("version", ""),
        "availability": agent.get("status", "UNKNOWN"),
        "workspace_support": agent.get("workspace_support", False),
        "headless_support": agent.get("headless_support", False),
        "adapter": agent.get("adapter", ""),
        "limitations": (agent.get("capabilities") or {}).get("limitations", []),
    }
