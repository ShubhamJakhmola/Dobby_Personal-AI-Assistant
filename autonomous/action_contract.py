"""Universal ActionRequest / ActionResult contract (Phase 19).

Every capability provider — browser, email, MCP, coding agent, terminal,
filesystem, phone, etc. — speaks this common interface so the
AutonomousExecutor can treat them uniformly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class ActionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SUCCESS = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    SKIPPED_DRY_RUN = "skipped_dry_run"
    IDEMPOTENT_SKIP = "idempotent_skip"
    NOT_CONFIGURED = "not_configured"
    NOT_SUPPORTED = "not_supported"


class RiskLevel(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    REVERSIBLE_LOCAL = "REVERSIBLE_LOCAL"
    REVERSIBLE_EXTERNAL = "REVERSIBLE_EXTERNAL"
    IRREVERSIBLE_EXTERNAL = "IRREVERSIBLE_EXTERNAL"
    SENSITIVE = "SENSITIVE"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"act-{uuid.uuid4().hex[:10]}"


@dataclass
class ActionRequest:
    """Standardised request sent to any capability provider."""

    action_id: str = field(default_factory=_new_id)
    goal_id: str = ""
    task_id: str = ""
    capability: str = ""           # e.g. "BROWSER", "EMAIL", "TERMINAL"
    provider: str = ""             # specific provider name
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout: int = 60              # seconds
    idempotency_key: str = ""
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL
    dry_run: bool = False
    created_at: str = field(default_factory=_now)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()}
        d["risk_level"] = self.risk_level.value
        return d


@dataclass
class ActionResult:
    """Standardised result returned by any capability provider."""

    action_id: str = ""
    status: ActionStatus = ActionStatus.PENDING
    output: Any = None
    error: str = ""
    verified: bool = False
    verification: dict = field(default_factory=dict)
    external_reference: str = ""   # confirmation ID from external service
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: str = field(default_factory=_now)

    @property
    def success(self) -> bool:
        return self.status == ActionStatus.COMPLETED

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()}
        d["status"] = self.status.value
        d["success"] = self.success
        return d

    @classmethod
    def ok(cls, action_id: str, output: Any = None, external_reference: str = "",
           metadata: dict | None = None) -> "ActionResult":
        return cls(action_id=action_id, status=ActionStatus.COMPLETED,
                   output=output, verified=True, external_reference=external_reference,
                   metadata=metadata or {})

    @classmethod
    def fail(cls, action_id: str, error: str, metadata: dict | None = None) -> "ActionResult":
        return cls(action_id=action_id, status=ActionStatus.FAILED,
                   error=error, metadata=metadata or {})

    @classmethod
    def dry_run(cls, action_id: str, metadata: dict | None = None) -> "ActionResult":
        return cls(action_id=action_id, status=ActionStatus.SKIPPED_DRY_RUN,
                   output="[dry-run: no action taken]", verified=False,
                   metadata=metadata or {})

    @classmethod
    def idempotent(cls, action_id: str, external_reference: str,
                   output: Any = None) -> "ActionResult":
        return cls(action_id=action_id, status=ActionStatus.IDEMPOTENT_SKIP,
                   output=output or "[idempotent: action already completed]",
                   verified=True, external_reference=external_reference)
