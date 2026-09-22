"""DAG-based task graph for the autonomous engine (Phase 19).

GoalTask is the Phase 19 unit of work within a Goal. It wraps the
existing Phase-2 Task/TaskManager but adds dependency tracking,
capability routing metadata, risk annotation, and structured retry policy.

The TaskGraph builds a topological ordering from the dependency DAG so
AutonomousExecutor can schedule steps correctly.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import uuid


class GoalTaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"          # all dependencies satisfied
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff_seconds: float = 2.0
    alternative_capability: str = ""    # fall back to this capability on failure


@dataclass
class GoalTask:
    """One step in an autonomous goal execution plan."""

    task_id: str = field(default_factory=lambda: f"gt-{uuid.uuid4().hex[:10]}")
    parent_goal: str = ""
    name: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)   # task_ids
    capability: str = ""                # e.g. "WEB", "BROWSER", "EMAIL"
    provider: str = ""                  # specific provider name
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_result: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    risk_level: str = "INFORMATIONAL"
    status: GoalTaskStatus = GoalTaskStatus.PENDING
    result: dict | None = None
    attempts: int = 0

    def is_ready(self, completed: set[str]) -> bool:
        return all(dep in completed for dep in self.dependencies)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()}
        d["status"] = self.status.value
        d["retry_policy"] = {
            "max_retries": self.retry_policy.max_retries,
            "backoff_seconds": self.retry_policy.backoff_seconds,
            "alternative_capability": self.retry_policy.alternative_capability,
        }
        return d


class TaskGraph:
    """DAG of GoalTasks with cycle detection and topological ordering."""

    def __init__(self, goal_id: str):
        self.goal_id = goal_id
        self._tasks: dict[str, GoalTask] = {}

    def add(self, task: GoalTask) -> GoalTask:
        task.parent_goal = self.goal_id
        self._tasks[task.task_id] = task
        return task

    def add_task(self, task: GoalTask) -> GoalTask:
        return self.add(task)

    def __len__(self) -> int:
        return len(self._tasks)

    def get(self, task_id: str) -> GoalTask | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[GoalTask]:
        return list(self._tasks.values())

    def is_valid(self) -> bool:
        try:
            self.topological_order()
            return True
        except ValueError:
            return False

    def topological_sort(self) -> list[GoalTask]:
        try:
            return self.topological_order()
        except ValueError:
            return []

    def topological_order(self) -> list[GoalTask]:
        """Return tasks in dependency-safe execution order (Kahn's algorithm).

        Raises ValueError if a cycle is detected.
        """
        in_degree: dict[str, int] = {tid: 0 for tid in self._tasks}
        for task in self._tasks.values():
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[task.task_id] += 1

        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        order: list[GoalTask] = []

        # adjacency: for each task, which tasks depend on it?
        dependents: dict[str, list[str]] = {tid: [] for tid in self._tasks}
        for task in self._tasks.values():
            for dep in task.dependencies:
                if dep in dependents:
                    dependents[dep].append(task.task_id)

        while queue:
            tid = queue.popleft()
            order.append(self._tasks[tid])
            for dependent_id in dependents[tid]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        if len(order) != len(self._tasks):
            raise ValueError("Circular dependency detected in TaskGraph")

        return order

    def ready_tasks(self, completed: set[str], failed: set[str]) -> list[GoalTask]:
        """Tasks whose dependencies are all completed (not failed/skipped)."""
        return [
            t for t in self._tasks.values()
            if t.status == GoalTaskStatus.PENDING
            and t.is_ready(completed)
            and not any(dep in failed for dep in t.dependencies)
        ]

    def mark_completed(self, task_id: str, result: dict) -> None:
        t = self._tasks[task_id]
        t.status = GoalTaskStatus.COMPLETED
        t.result = result

    def mark_failed(self, task_id: str, error: str) -> None:
        t = self._tasks[task_id]
        t.status = GoalTaskStatus.FAILED
        t.result = {"error": error}

    def mark_running(self, task_id: str) -> None:
        self._tasks[task_id].status = GoalTaskStatus.RUNNING

    def is_complete(self) -> bool:
        return all(
            t.status in {GoalTaskStatus.COMPLETED, GoalTaskStatus.SKIPPED}
            for t in self._tasks.values()
        )

    def has_failures(self) -> bool:
        return any(t.status == GoalTaskStatus.FAILED for t in self._tasks.values())

    def completed_ids(self) -> set[str]:
        return {
            t.task_id for t in self._tasks.values()
            if t.status == GoalTaskStatus.COMPLETED
        }

    def failed_ids(self) -> set[str]:
        return {
            t.task_id for t in self._tasks.values()
            if t.status == GoalTaskStatus.FAILED
        }

    def summary(self) -> dict:
        statuses: dict[str, int] = {}
        for t in self._tasks.values():
            statuses[t.status.value] = statuses.get(t.status.value, 0) + 1
        return {
            "goal_id": self.goal_id,
            "total": len(self._tasks),
            "by_status": statuses,
            "complete": self.is_complete(),
        }

    def as_list(self) -> list[dict]:
        return [t.as_dict() for t in self._tasks.values()]

    @classmethod
    def from_plan(cls, goal_id: str, plan_steps: list[dict]) -> "TaskGraph":
        """Build a TaskGraph from a list of structured plan step dicts."""
        graph = cls(goal_id)
        id_map: dict[str, str] = {}   # step name → task_id

        for step in plan_steps:
            deps_by_name = step.get("dependencies", [])
            task = GoalTask(
                parent_goal=goal_id,
                name=step.get("name", ""),
                description=step.get("description", ""),
                dependencies=[id_map[d] for d in deps_by_name if d in id_map],
                capability=step.get("capability", ""),
                provider=step.get("provider", ""),
                parameters=step.get("parameters", {}),
                expected_result=step.get("expected_result", {}),
                verification=step.get("verification", {}),
                retry_policy=RetryPolicy(**step["retry_policy"])
                    if "retry_policy" in step else RetryPolicy(),
                risk_level=step.get("risk_level", "INFORMATIONAL"),
            )
            graph.add(task)
            id_map[step.get("name", task.task_id)] = task.task_id

        return graph
