from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentState:
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DESTROYED = "destroyed"


@dataclass
class AgentSpec:
    agent_id: str
    name: str
    purpose: str
    agent_type: str = "temporary"
    parent_task_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    brain_requirements: dict[str, Any] = field(default_factory=dict)
    brain: dict[str, Any] = field(default_factory=dict)
    context_requirements: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, int] = field(default_factory=lambda: {"max_runtime_seconds": 900, "max_steps": 50, "max_retries": 3})
    verification: dict[str, Any] = field(default_factory=lambda: {"required": True})
    persistent: bool = False
    state: str = AgentState.CREATED
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentResult:
    agent_id: str
    status: str
    success: bool
    content: str = ""
    structured_data: dict | None = None
    verification: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)