from __future__ import annotations

from agent.executor import execute
from agent.planner import Planner, TaskPlan
from agent.recovery import recover
from agent.task_manager import TaskManager, TaskState
from agent.verifier import verify
from datetime import datetime, timezone
import time


class Workflow:
    """Run PLAN -> EXECUTE -> VERIFY -> RECOVER without claiming unverified success."""

    def __init__(self, planner: Planner | None = None, tasks: TaskManager | None = None):
        self.planner = planner or Planner()
        self.tasks = tasks or TaskManager()

    def run(self, task_id: str, plan: TaskPlan, max_runtime: float | None = None, resume: bool = False) -> dict:
        task = self.tasks.get(task_id) if resume else None
        task = task or self.tasks.create(task_id, plan.goal)
        task.state = TaskState.RUNNING
        started = time.monotonic()
        for step in plan.steps:
            if task.state == TaskState.CANCELLED:
                break
            if resume and step.name in task.completed_steps:
                continue
            if step.depends_on and not all(name in task.completed_steps for name in step.depends_on):
                task.failed_steps.append(step.name)
                task.state = TaskState.FAILED
                task.results.append({"step": step.name, "success": False, "status": "failed",
                                     "error_category": "dependency_failed", "error": "a prerequisite step failed"})
                self.tasks._save()
                return {"success": False, "state": task.state.value, "results": task.results}
            result = execute(step)
            if result.success:
                verification = verify(step, result.value)
                result.verification = verification.as_dict()
                result.verified = verification.verified
            if result.success and not result.verified:
                result.success = False
                result.status = "verification_failed"
                result.error = "verification failed"
            if not result.success:
                result = recover(step, result)
                if result.success:
                    verification = verify(step, result.value)
                    result.verification = verification.as_dict()
                    result.verified = verification.verified
                if result.success and not result.verified:
                    result.success = False
                    result.status = "verification_failed"
                    result.error = "verification failed after recovery"
            task.current_step = step.name
            task.updated_at = datetime.now(timezone.utc).isoformat()
            task.results.append(result.as_dict())
            if result.verified:
                task.completed_steps.append(step.name)
            else:
                task.failed_steps.append(step.name)
            if max_runtime is not None and time.monotonic() - started > max_runtime:
                task.state = TaskState.FAILED
                task.results[-1]["status"] = "timeout"
                self.tasks._save()
                return {"success": False, "state": task.state.value, "results": task.results}
            if not result.success:
                task.state = TaskState.FAILED
                self.tasks._save()
                return {"success": False, "state": task.state.value, "results": task.results}
        task.state = TaskState.CANCELLED if task.state == TaskState.CANCELLED else TaskState.COMPLETED
        self.tasks._save()
        return {"success": task.state == TaskState.COMPLETED, "state": task.state.value, "results": task.results}