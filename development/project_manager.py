from __future__ import annotations

from pathlib import Path

from development.workspace import WorkspaceManager


class ProjectManager:
    def __init__(self, root: str | Path | None = None):
        self.workspaces = WorkspaceManager(root)

    def create_project(self, name: str) -> dict:
        return self.workspaces.create_project(name).as_dict()

    def locate_project(self, name: str) -> dict | None:
        workspace = self.workspaces.locate_project(name)
        return workspace.as_dict() if workspace else None

    def validate_project(self, path: str | Path) -> dict:
        valid, reason = self.workspaces.validate_workspace(path)
        return {"valid": valid, "reason": reason}

    def read_project_state(self, path: str | Path) -> dict:
        return self.workspaces.read_state(path).as_dict()

    def update_project_state(self, path: str | Path, **updates) -> dict:
        return self.workspaces.update_state(path, **updates).as_dict()

    def status(self) -> dict:
        data = self.workspaces.status()
        data["projects"] = self.workspaces.list_projects()
        return data
