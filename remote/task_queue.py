from __future__ import annotations

import time
from collections import deque


class TaskQueue:
    def __init__(self, *, max_pending_tasks: int = 16, max_running_tasks: int = 4, heartbeat_timeout: int = 30):
        self.max_pending_tasks = max_pending_tasks
        self.max_running_tasks = max_running_tasks
        self.heartbeat_timeout = heartbeat_timeout
        self._pending: deque = deque()
        self._results: dict[str, dict] = {}
        self._seen: set[str] = set()

    def enqueue(self, task):
        if len(self._pending) >= self.max_pending_tasks:
            raise OverflowError("max queue size exceeded")
        if task.task_id in self._seen:
            return False
        self._seen.add(task.task_id)
        self._pending.append(task)
        return True

    def pending(self):
        return list(self._pending)

    def duplicate(self, task_id: str) -> bool:
        return task_id in self._seen

    def add_result(self, task_id: str, result):
        self._results[task_id] = result.as_dict() if hasattr(result, "as_dict") else result
        return True

    def state_for(self, session):
        last_activity = float(session.get("last_activity", time.time()))
        age = time.time() - last_activity
        if age > 300:
            return "OFFLINE"
        if age > self.heartbeat_timeout:
            return "DEGRADED"
        return session.get("state", "ONLINE")
