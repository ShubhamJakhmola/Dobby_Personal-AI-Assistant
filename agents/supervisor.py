from __future__ import annotations

import time

from agents.lifecycle import transition
from agents.models import AgentResult, AgentState
from brain.request import BrainRequest


class AgentSupervisor:
    """Runs worker reasoning under limits; OS actions remain Dobby-mediated."""
    def __init__(self, brain_router, agent_registry):
        self.brain_router = brain_router
        self.agent_registry = agent_registry

    def run(self, agent_id: str, task: str) -> dict:
        spec = self.agent_registry.get(agent_id)
        if not spec:
            return AgentResult(agent_id, AgentState.FAILED, False, errors=["agent not found"]).as_dict()
        transition(spec, AgentState.RUNNING)
        started = time.monotonic()
        request = BrainRequest(task=task, task_type=spec.brain_requirements.get("task_type", "analysis"),
                               complexity=spec.brain_requirements.get("complexity", "medium"),
                               required_capabilities=spec.brain_requirements.get("capabilities", ["reasoning"]),
                               privacy_level=spec.brain_requirements.get("privacy", "any"),
                               preferred_provider=spec.brain.get("provider", ""), role="specialist",
                               max_context=spec.limits.get("max_context", 6000),
                               metadata={"agent_id": agent_id, "task_id": spec.parent_task_id})
        result = self.brain_router.route(request)
        if result.get("status") == "completed":
            transition(spec, AgentState.COMPLETED)
            if spec.persistent:
                self.agent_registry.persistence.save(spec)
            return AgentResult(agent_id, AgentState.COMPLETED, True, result.get("content", ""),
                               result.get("structured_data"), {"verified": False, "reason": "worker result requires Dobby verification"},
                               metadata={"duration": time.monotonic() - started, "brain": result.get("provider")}).as_dict()
        transition(spec, AgentState.FAILED)
        if spec.persistent:
            self.agent_registry.persistence.save(spec)
        return AgentResult(agent_id, AgentState.FAILED, False, errors=result.get("errors", [result.get("reason", "worker failed")]),
                           metadata={"duration": time.monotonic() - started}).as_dict()