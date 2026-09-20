from __future__ import annotations

from datetime import datetime, timezone

from agents.models import AgentState


def transition(spec, state: str) -> None:
    allowed = {
        AgentState.CREATED: {AgentState.RUNNING, AgentState.DESTROYED},
        AgentState.RUNNING: {AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED},
        AgentState.COMPLETED: {AgentState.DESTROYED},
        AgentState.FAILED: {AgentState.DESTROYED},
        AgentState.CANCELLED: {AgentState.DESTROYED},
        AgentState.DESTROYED: set(),
    }
    if state not in allowed.get(spec.state, set()):
        raise ValueError(f"invalid agent lifecycle transition: {spec.state} -> {state}")
    spec.state = state
    spec.updated_at = datetime.now(timezone.utc).isoformat()