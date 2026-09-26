from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ComputerResult:
    success: bool
    status: str
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    error_category: str | None = None
    error: str | None = None
    verified: bool = False
    verification: dict | None = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Monitor:
    index: int
    left: int
    top: int
    width: int
    height: int
    primary: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class FrameResult:
    success: bool
    monitor: int | None
    width: int = 0
    height: int = 0
    encoding: str = ""
    backend: str = ""
    timestamp: str = field(default_factory=now_iso)
    black_frame: bool = False
    near_black_ratio: float = 0.0
    pixel_variance: float = 0.0
    frame: bytes | None = None
    error_category: str | None = None
    error: str | None = None

    def as_dict(self, include_frame: bool = False) -> dict:
        data = asdict(self)
        if not include_frame:
            data.pop("frame", None)
        elif self.frame is not None:
            data["frame"] = self.frame.hex()
        return data