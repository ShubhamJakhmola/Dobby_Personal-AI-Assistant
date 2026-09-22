"""Goal model for Dobby's autonomous engine (Phase 19)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class GoalStatus(str, Enum):
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    COMPLETED_UNVERIFIED = "COMPLETED_UNVERIFIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"goal-{uuid.uuid4().hex[:12]}"


@dataclass
class Goal:
    """Structured representation of a high-level user goal."""

    goal_id: str = field(default_factory=_new_id)
    original_request: str = ""
    normalized_objective: str = ""
    constraints: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    deadline: str | None = None
    priority: int = 5                      # 1 (highest) – 10 (lowest)
    success_criteria: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    sensitivity: str = "normal"           # normal | sensitive | restricted
    status: GoalStatus = GoalStatus.CREATED
    task_graph_id: str = ""               # links to TaskGraph
    dry_run: bool = False
    plan: list[dict] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    # ---- helpers -------------------------------------------------------

    def touch(self) -> None:
        self.updated_at = _now()

    def transition(self, new_status: GoalStatus) -> None:
        self.status = new_status
        self.touch()

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()}
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Goal":
        data = dict(data)
        raw = data.pop("status", GoalStatus.CREATED.value)
        status = GoalStatus(raw) if isinstance(raw, str) else raw
        return cls(status=status, **data)

    def summary(self) -> dict:
        """Compact summary for CLI / dashboard display."""
        return {
            "goal_id": self.goal_id,
            "status": self.status.value,
            "priority": self.priority,
            "objective": self.normalized_objective or self.original_request,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
