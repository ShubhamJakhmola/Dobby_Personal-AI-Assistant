from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CodingAgentState(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    FOUND = "FOUND"
    INSTALLED = "INSTALLED"
    CONFIGURED = "CONFIGURED"
    AVAILABLE = "AVAILABLE"
    RUNNING = "RUNNING"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class CodingAgentResultStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    COMPLETED_UNVERIFIED = "completed_unverified"


@dataclass
class CodingAgentCapabilities:
    workspace: bool = False
    headless: bool = False
    noninteractive: bool = False
    output_capture: bool = True
    invocation_styles: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CodingAgentInfo:
    id: str
    name: str
    provider: str
    adapter: str
    executable: str = ""
    version: str = ""
    status: CodingAgentState = CodingAgentState.NOT_FOUND
    installed: bool = False
    configured: bool = False
    available: bool = False
    capabilities: CodingAgentCapabilities = field(default_factory=CodingAgentCapabilities)
    workspace_support: bool = False
    headless_support: bool = False
    noninteractive_support: bool = False
    output_format: str = "text"
    authentication_status: str = "unknown"
    last_health_check: str = ""
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class CodingTask:
    project_id: str
    objective: str
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    files_in_scope: list[str] = field(default_factory=list)
    files_out_of_scope: list[str] = field(default_factory=list)
    test_requirements: list[str] = field(default_factory=list)
    design_context: str = ""
    previous_failures: list[str] = field(default_factory=list)
    timeout: float = 300
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> tuple[bool, str]:
        if not self.project_id.strip():
            return False, "project_id is required"
        if not self.objective.strip():
            return False, "objective is required"
        if self.timeout <= 0:
            return False, "timeout must be positive"
        return True, "valid"

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CommandResult:
    status: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    timed_out: bool = False
    cancelled: bool = False
    truncated: bool = False
    command: list[str] = field(default_factory=list)
    workspace: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == "completed" and self.exit_code == 0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CodingAgentResult:
    status: CodingAgentResultStatus
    summary: str = ""
    files_changed: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    commands_executed: list[list[str]] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    test_results: dict[str, Any] = field(default_factory=dict)
    build_result: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_output_reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class ProjectState:
    project_id: str
    name: str
    status: str = "created"
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    current_phase: str = "phase9"
    active_agent: str = ""
    last_task: str = ""
    last_result: str = ""
    tests: dict[str, Any] = field(default_factory=lambda: {"status": "not_run", "passed": 0, "failed": 0})

    def touch(self) -> None:
        self.updated_at = now()

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Workspace:
    project_id: str
    name: str
    path: Path
    metadata_path: Path

    def as_dict(self) -> dict:
        return {"project_id": self.project_id, "name": self.name, "path": str(self.path), "metadata_path": str(self.metadata_path)}
