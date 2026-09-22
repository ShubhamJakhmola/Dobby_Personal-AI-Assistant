"""Bounded ContextBuilder — assembles ContextPacket for Gemini (Phase 19).

Includes only what is relevant to the current goal:
  - goal description + status
  - current plan step
  - recent results (capped)
  - relevant memory (fetched from MemoryManager)
  - capability statuses

Never forwards the entire memory database or full conversation history.
"""
from __future__ import annotations

from typing import Any


_MAX_RESULTS = 10
_MAX_MEMORY_CHARS = 2000
_MAX_CAPABILITIES = 20


class ContextBuilder:
    """Build a bounded context packet for the master brain."""

    def __init__(self, memory_manager=None, capability_registry=None):
        self._memory = memory_manager
        self._cap_registry = capability_registry

    def build_context(self, goal: Any, current_step: str = "", recent_results: list[dict] | None = None) -> Any:
        from dataclasses import dataclass, field
        @dataclass
        class BoundedPacket:
            task: str
            messages: list[dict] = field(default_factory=list)
            step: str = ""
            results: list[dict] = field(default_factory=list)

            def as_dict(self) -> dict:
                return {"task": self.task, "messages": self.messages, "step": self.step, "results": self.results}

        objective = goal.normalized_objective or goal.original_request if hasattr(goal, "original_request") else str(goal)
        msgs = [{"role": "system", "content": f"Goal: {objective}"}]
        return BoundedPacket(
            task=getattr(goal, "original_request", objective),
            messages=msgs,
            step=current_step,
            results=recent_results or [],
        )

    def build(
        self,
        goal: Any,                           # Goal
        current_task: Any | None = None,     # GoalTask | None
        recent_results: list[dict] | None = None,
        max_results: int = _MAX_RESULTS,
    ) -> dict:
        """Return a dict suitable for inclusion in a BrainRequest context."""
        packet: dict[str, Any] = {
            "goal_id": goal.goal_id,
            "objective": goal.normalized_objective or goal.original_request,
            "status": goal.status.value,
            "priority": goal.priority,
            "success_criteria": goal.success_criteria,
            "constraints": goal.constraints,
        }

        if current_task is not None:
            packet["current_step"] = {
                "task_id": current_task.task_id,
                "name": current_task.name,
                "capability": current_task.capability,
                "description": current_task.description,
            }

        if recent_results:
            packet["recent_results"] = recent_results[-max_results:]

        # Relevant memory (only if memory manager available)
        if self._memory:
            memory_snippet = self._fetch_relevant_memory(goal)
            if memory_snippet:
                packet["relevant_memory"] = memory_snippet

        # Capability statuses (brief)
        if self._cap_registry:
            statuses = self._cap_registry.status()
            packet["capabilities"] = statuses[:_MAX_CAPABILITIES]

        return packet

    # ── Helpers ────────────────────────────────────────────────────────────

    def _fetch_relevant_memory(self, goal: Any) -> str:
        """Pull relevant memory without dumping entire store."""
        try:
            query = goal.normalized_objective or goal.original_request
            # Use search_memory if available, else format_memory_for_prompt
            if hasattr(self._memory, "search_memory"):
                results = self._memory.search_memory(query)
                if isinstance(results, dict):
                    text = "\n".join(
                        f"{k}: {v}" for k, v in results.items() if v
                    )
                else:
                    text = str(results)
            elif hasattr(self._memory, "format_memory_for_prompt"):
                text = self._memory.format_memory_for_prompt()
            else:
                return ""
            # Hard cap to avoid flooding context
            return text[:_MAX_MEMORY_CHARS]
        except Exception:
            return ""
