from __future__ import annotations

import subprocess
from pathlib import Path

from development.models import CodingAgentResultStatus
from development.workspace import WorkspaceManager


def inspect_workspace_changes(workspace: str | Path) -> dict:
    path = Path(workspace)
    if not (path / ".git").exists():
        return {"git": "not_repository", "changed_files": []}
    status = subprocess.run(["git", "status", "--short"], cwd=path, capture_output=True, text=True, timeout=10, check=False)
    changed = [line[3:] for line in status.stdout.splitlines() if len(line) > 3]
    return {"git": "available", "changed_files": changed, "raw_status": status.stdout[:4000]}


def verify_agent_result(workspace: str | Path, result: dict, acceptance_criteria: list[str] | None = None,
                        workspace_manager: WorkspaceManager | None = None) -> dict:
    manager = workspace_manager or WorkspaceManager(Path(workspace).parent)
    valid, reason = manager.validate_workspace(workspace)
    if not valid:
        return {"status": CodingAgentResultStatus.FAILED.value, "verified": False, "reason": reason}
    changes = inspect_workspace_changes(workspace)
    accepted = bool(result.get("status") in {"completed_unverified", "completed"})
    criteria = acceptance_criteria or []
    status = CodingAgentResultStatus.COMPLETED_UNVERIFIED.value if accepted else CodingAgentResultStatus.FAILED.value
    return {"status": status, "verified": False, "reason": "Dobby verification requires build/tests/criteria checks",
            "acceptance_criteria": criteria, "changes": changes}
