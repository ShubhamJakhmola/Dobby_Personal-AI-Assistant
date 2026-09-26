from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CandidateStatus:
    DISCOVERED = "DISCOVERED"
    INSPECTING = "INSPECTING"
    REJECTED = "REJECTED"
    SANDBOXED = "SANDBOXED"
    TESTING = "TESTING"
    APPROVED = "APPROVED"
    INSTALLED = "INSTALLED"
    ADAPTED = "ADAPTED"
    REGISTERED = "REGISTERED"
    FAILED = "FAILED"


@dataclass
class CapabilityRequest:
    request_id: str
    name: str
    description: str
    required_operations: list[str] = field(default_factory=list)
    runtime: str = "python"
    constraints: dict[str, Any] = field(default_factory=lambda: {"open_source": True, "free": True, "local_preferred": True, "network_required": False})

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CandidateRepository:
    candidate_id: str
    name: str
    owner: str = ""
    url: str = ""
    description: str = ""
    language: str = ""
    license: str = ""
    default_branch: str = ""
    latest_release: str = ""
    last_activity: str = ""
    stars: int = 0
    forks: int = 0
    dependencies: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)
    candidate_path: str = ""
    commit_sha: str = ""
    status: str = CandidateStatus.DISCOVERED
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)

    def as_dict(self) -> dict:
        return asdict(self)