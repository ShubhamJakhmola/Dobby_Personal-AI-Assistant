from __future__ import annotations

import re
import uuid

from agents.capabilities import missing_capabilities
from agents.models import AgentSpec
from agents.policy import validate_agent_scope


class AgentFactory:
    def __init__(self, action_registry, brain_router, agent_registry=None):
        self.action_registry = action_registry
        self.brain_router = brain_router
        self.agent_registry = agent_registry

    def should_create(self, task: str, *, task_type: str = "general", complexity: str = "medium",
                      required_capabilities: list[str] | None = None) -> tuple[bool, str]:
        capabilities = required_capabilities or []
        if task_type in {"simple", "direct", "command", "file_create"} and not capabilities:
            return False, "direct execution is sufficient"
        if complexity.lower() == "high" or len(capabilities) > 1 or task_type in {"investigation", "research", "analysis", "review"}:
            return True, "task requires bounded specialist orchestration"
        return False, "direct execution is sufficient"

    def create_spec(self, purpose: str, *, parent_task_id: str = "", name: str = "worker",
                    agent_type: str = "temporary", capabilities: list[str] | None = None,
                    brain_requirements: dict | None = None, context_requirements: dict | None = None,
                    limits: dict | None = None, persistent: bool = False, metadata: dict | None = None) -> dict:
        capabilities = capabilities or []
        missing = missing_capabilities(capabilities, self.action_registry)
        if missing:
            return {"success": False, "status": "failed", "error_category": "capability_unavailable",
                    "error": f"unavailable capabilities: {', '.join(missing)}"}
        spec = AgentSpec(str(uuid.uuid4()), re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "worker",
                         purpose, agent_type, parent_task_id, capabilities,
                         brain_requirements or {}, {}, context_requirements or {},
                         limits or {"max_runtime_seconds": 900, "max_steps": 50, "max_retries": 3},
                         {"required": True}, persistent=persistent, metadata=metadata or {})
        valid, reason = validate_agent_scope(spec, self.action_registry)
        if not valid:
            return {"success": False, "status": "failed", "error_category": "policy_denied", "error": reason}
        from brain.request import BrainRequest
        request = BrainRequest(task=purpose, task_type=spec.brain_requirements.get("task_type", "analysis"),
                               complexity=spec.brain_requirements.get("complexity", "medium"),
                               required_capabilities=spec.brain_requirements.get("capabilities", ["reasoning"]),
                               privacy_level=spec.brain_requirements.get("privacy", "any"), role="specialist")
        decision = self.brain_router.route(request, dry_run=True)
        if decision.get("status") == "unavailable":
            return {"success": False, "status": "failed", "error_category": "brain_unavailable", "error": decision["reason"]}
        spec.brain = {"provider": decision["provider"], "model": decision["model"], "routing": decision}
        if self.agent_registry:
            self.agent_registry.register(spec)
        return {"success": True, "status": "created", "spec": spec.as_dict()}

    def create_coding_spec(self, purpose: str, coding_agent_id: str, *, parent_task_id: str = "",
                           limits: dict | None = None) -> dict:
        from development.agent_registry import CodingAgentRegistry
        registry = CodingAgentRegistry()
        agent = registry.get(coding_agent_id)
        if not agent:
            return {"success": False, "status": "failed", "error_category": "coding_agent_not_found",
                    "error": f"coding agent not found: {coding_agent_id}"}
        if not agent.get("available"):
            return {"success": False, "status": "failed", "error_category": "coding_agent_unavailable",
                    "error": f"coding agent is {agent.get('status', 'UNKNOWN')}", "agent": agent}
        return self.create_spec(purpose, parent_task_id=parent_task_id, name=f"coding_{coding_agent_id}",
                                agent_type="temporary", capabilities=[f"coding_agent.{coding_agent_id}"],
                                brain_requirements={"task_type": "coding", "capabilities": ["reasoning"], "privacy": "local"},
                                limits=limits or {"max_runtime_seconds": 900, "max_steps": 20, "max_retries": 2},
                                persistent=False, metadata={"coding_agent_id": coding_agent_id, "executable": agent.get("executable", "")})
