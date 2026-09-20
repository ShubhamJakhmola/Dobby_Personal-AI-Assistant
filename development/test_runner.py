from __future__ import annotations

import shlex
from pathlib import Path

from development.adapters.generic_cli import GenericCliAdapter
from development.workspace import WorkspaceManager


class TestRunner:
    def __init__(self, workspace_manager: WorkspaceManager | None = None):
        self.workspace_manager = workspace_manager or WorkspaceManager()

    def run(self, workspace: str | Path, command: str | list[str], timeout: float = 120) -> dict:
        valid, reason = self.workspace_manager.validate_workspace(workspace)
        if not valid:
            return {"success": False, "status": "blocked", "error": reason}
        parts = command if isinstance(command, list) else shlex.split(command)
        if not parts:
            return {"success": False, "status": "blocked", "error": "test command is required"}
        result = GenericCliAdapter(parts[0], parts[1:], task_arg=False, timeout=timeout).run_command(parts, Path(workspace), timeout)
        self.workspace_manager.append_event(workspace, "tests_finished", result.as_dict())
        return result.as_dict() | {"success": result.success}
