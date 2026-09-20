from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TaskContext:
    request: str
    topic: str = ""
    active_project: str = ""
    entities: dict = field(default_factory=dict)
    recent_goals: list[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update_topic(self, topic: str) -> None:
        self.topic = topic.strip()
        self.updated_at = datetime.now(timezone.utc).isoformat()