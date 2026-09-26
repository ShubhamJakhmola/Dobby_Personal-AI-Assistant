from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import os
from datetime import datetime, timezone
from pathlib import Path


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    task_id: str
    goal: str
    state: TaskState = TaskState.PENDING
    results: list[dict] = field(default_factory=list)
    plan: list[dict] = field(default_factory=list)
    current_step: str = ""
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    verification_results: list[dict] = field(default_factory=list)
    recovery_attempts: list[dict] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskManager:
    def __init__(self, storage_path: str | Path | None = None):
        self.tasks: dict[str, Task] = {}
        default = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby")) / "tasks.json"
        self.storage_path = Path(storage_path) if storage_path else default
        self._load()

    def create(self, task_id: str, goal: str) -> Task:
        task = Task(task_id, goal)
        self.tasks[task_id] = task
        self._save()
        return task

    def get(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    def cancel(self, task_id: str) -> None:
        self.tasks[task_id].state = TaskState.CANCELLED
        self.tasks[task_id].updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: {**task.__dict__, "state": task.state.value} for key, task in self.tasks.items()}
        self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load(self) -> None:
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        for task_id, raw in data.items():
            raw["state"] = TaskState(raw.get("state", TaskState.PENDING.value))
            self.tasks[task_id] = Task(task_id=task_id, **{key: value for key, value in raw.items() if key != "task_id"})