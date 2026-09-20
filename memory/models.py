from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ContextState:
    topic: str = ""
    project: str = ""
    active_task: str = ""
    device: str = ""
    constraints: list[str] = field(default_factory=list)
    recent_intent: str = ""
    working_directory: str = ""
    execution_state: str = ""
    updated_at: str = field(default_factory=timestamp)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConversationEntry:
    role: str
    message: str
    timestamp: str = field(default_factory=timestamp)
    task: str = ""
    project: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class MemoryRecord:
    id: str
    category: str
    key: str
    value: str
    confidence: float = 1.0
    source: str = "user"
    created_at: str = field(default_factory=timestamp)
    updated_at: str = field(default_factory=timestamp)
    topic: str = ""
    project: str = ""
    task: str = ""
    relevance: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectContext:
    name: str
    workspace: str = ""
    repository: str = ""
    branch: str = ""
    technology: list[str] = field(default_factory=list)
    current_goal: str = ""
    instructions: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    recent_failures: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=timestamp)

    def as_dict(self) -> dict:
        return asdict(self)