from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from development.models import ProjectState, Workspace, now
from development.redaction import redact


def default_workspace_root() -> Path:
    configured = os.environ.get("DOBBY_PROJECT_ROOT", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".dobby" / "projects"


def safe_project_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip()).strip("._")
    return cleaned or "project"


class WorkspaceManager:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root).expanduser() if root else default_workspace_root()

    def status(self) -> dict:
        return {"root": str(self.root), "writable": self._writable(), "valid": self.root.exists() or self.root.parent.exists()}

    def _writable(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            probe = self.root / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def create_project(self, name: str) -> Workspace:
        project_name = safe_project_name(name)
        path = self.root / project_name
        self._ensure_inside_root(path)
        metadata = path / ".dobby"
        metadata.mkdir(parents=True, exist_ok=True)
        for filename in ("SPEC.md", "PLAN.md", "ACCEPTANCE.md", "DESIGN.md"):
            target = metadata / filename
            if not target.exists():
                target.write_text(f"# {project_name}\n", encoding="utf-8")
        state_path = metadata / "STATE.json"
        if state_path.exists():
            state = self.read_state(path)
            project_id = state.project_id
        else:
            project_id = str(uuid.uuid4())
            self.write_state(path, ProjectState(project_id, project_name))
        for filename in ("AGENT_LOG.jsonl", "ERRORS.jsonl"):
            (metadata / filename).touch(exist_ok=True)
        return Workspace(project_id, project_name, path, metadata)

    def locate_project(self, name: str) -> Workspace | None:
        path = self.root / safe_project_name(name)
        if not path.exists():
            return None
        self._ensure_inside_root(path)
        state = self.read_state(path)
        return Workspace(state.project_id, state.name, path, path / ".dobby")

    def list_projects(self) -> list[dict]:
        if not self.root.exists():
            return []
        items = []
        for path in sorted(self.root.iterdir()):
            if path.is_dir() and (path / ".dobby" / "STATE.json").exists():
                state = self.read_state(path)
                items.append({"name": state.name, "project_id": state.project_id, "path": str(path), "status": state.status})
        return items

    def validate_workspace(self, workspace: str | Path) -> tuple[bool, str]:
        try:
            path = Path(workspace).resolve()
            self._ensure_inside_root(path)
            if not (path / ".dobby" / "STATE.json").exists():
                return False, "workspace is missing .dobby/STATE.json"
            return True, "valid"
        except Exception as exc:
            return False, str(exc)

    def read_state(self, workspace: str | Path) -> ProjectState:
        data = json.loads((Path(workspace) / ".dobby" / "STATE.json").read_text(encoding="utf-8"))
        return ProjectState(**data)

    def write_state(self, workspace: str | Path, state: ProjectState) -> None:
        state.touch()
        path = Path(workspace) / ".dobby" / "STATE.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(redact(state.as_dict()), indent=2), encoding="utf-8")

    def update_state(self, workspace: str | Path, **updates) -> ProjectState:
        state = self.read_state(workspace)
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        self.write_state(workspace, state)
        return state

    def append_event(self, workspace: str | Path, event: str, metadata: dict | None = None, *, errors: bool = False) -> None:
        valid, reason = self.validate_workspace(workspace)
        if not valid:
            raise ValueError(reason)
        record = {"timestamp": now(), "event": event, "metadata": redact(metadata or {})}
        filename = "ERRORS.jsonl" if errors else "AGENT_LOG.jsonl"
        with (Path(workspace) / ".dobby" / filename).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")

    def _ensure_inside_root(self, path: Path) -> None:
        root = self.root.resolve()
        target = path.resolve()
        if root != target and root not in target.parents:
            raise ValueError("workspace path escapes configured project root")


class WorkspaceBoundary:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()

    def contains(self, path: str | Path) -> bool:
        target = Path(path).resolve()
        return target == self.workspace or self.workspace in target.parents
