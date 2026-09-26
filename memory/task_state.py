from __future__ import annotations

from agent.task_manager import TaskManager


class TaskStateStore:
    """Compatibility facade over the existing persisted task-state system."""
    def __init__(self, path=None):
        self.manager = TaskManager(path)

    def get(self, task_id):
        task = self.manager.get(task_id)
        return task.__dict__ if task else None

    def status(self) -> dict:
        return {"available": True, "count": len(self.manager.tasks), "path": str(self.manager.storage_path)}