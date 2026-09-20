from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeviceState(str, Enum):
    UNKNOWN = "UNKNOWN"
    ENROLLING = "ENROLLING"
    AUTHENTICATED = "AUTHENTICATED"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


@dataclass
class DeviceIdentity:
    device_id: str
    device_name: str
    platform: str
    architecture: str
    client_version: str
    enrollment_token: str = ""
    public_key: str = ""
    private_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DeviceCapability:
    id: str
    version: str = "1"
    supported: bool = True
    platform: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DeviceSession:
    session_id: str
    device_id: str
    authenticated: bool = False
    online: bool = True
    last_seen: str = field(default_factory=now_iso)
    capabilities: list[DeviceCapability] = field(default_factory=list)
    policy_version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RemoteTask:
    task_id: str
    device_id: str
    capability: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    requested_by: str = "dobby-core"
    policy_metadata: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    correlation_id: str = ""
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RemoteTaskResult:
    task_id: str
    device_id: str
    status: str = "ACCEPTED"
    started_at: str = field(default_factory=now_iso)
    completed_at: str = field(default_factory=now_iso)
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    verification: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)
