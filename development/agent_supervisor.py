from __future__ import annotations

from pathlib import Path

from development.adapters.generic_cli import GenericCliAdapter
from development.models import CodingAgentResult, CodingAgentResultStatus, CodingTask
from development.workspace import WorkspaceManager


class CodingAgentSupervisor:
    def __init__(self, workspace_manager: WorkspaceManager | None = None, max_retries: int = 2):
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.max_retries = max(0, max_retries)

    def run_generic(self, executable: str, workspace: str | Path, task: CodingTask, args: list[str] | None = None) -> dict:
        valid, reason = self.workspace_manager.validate_workspace(workspace)
        if not valid:
            return CodingAgentResult(CodingAgentResultStatus.BLOCKED, errors=[reason]).as_dict()
        self.workspace_manager.append_event(workspace, "agent_started", {"agent": executable, "task": task.objective[:500]})
        result = GenericCliAdapter(executable, args or [], timeout=task.timeout).start(Path(workspace), task)
        self.workspace_manager.append_event(workspace, "agent_stopped", result.as_dict(), errors=result.status == CodingAgentResultStatus.FAILED)
        return result.as_dict()

    def create_repair_task(self, task: CodingTask, failure: str) -> CodingTask:
        failures = [*task.previous_failures, failure[:2000]][-self.max_retries:]
        return CodingTask(task.project_id, f"Repair failure for: {task.objective}", task.requirements,
                          task.constraints, task.acceptance_criteria, task.files_in_scope,
                          task.files_out_of_scope, task.test_requirements, task.design_context,
                          failures, task.timeout, {**task.metadata, "repair": True})
