from __future__ import annotations

from agents.lifecycle import transition
from agents.models import AgentState
from agents.persistence import AgentPersistence


class AgentRegistry:
    def __init__(self, persistence=None):
        self.persistence = persistence or AgentPersistence()
        self._agents = {}

    def register(self, spec) -> None:
        self._agents[spec.agent_id] = spec
        if spec.persistent:
            self.persistence.save(spec)

    def get(self, agent_id: str):
        return self._agents.get(agent_id)

    def list(self) -> list[dict]:
        return [spec.as_dict() for spec in self._agents.values()]

    def destroy(self, agent_id: str) -> bool:
        spec = self._agents.get(agent_id)
        if not spec:
            return False
        if spec.state != AgentState.DESTROYED:
            transition(spec, AgentState.DESTROYED)
        if not spec.persistent:
            self._agents.pop(agent_id, None)
        else:
            self.persistence.save(spec)
        return True

    def status(self) -> dict:
        return {"available": True, "count": len(self._agents),
                "temporary": sum(not item.persistent for item in self._agents.values()),
                "persistent": sum(item.persistent for item in self._agents.values())}