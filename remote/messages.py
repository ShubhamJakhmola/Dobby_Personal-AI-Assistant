from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DeviceMessage:
    type: str
    device_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""

    def as_dict(self) -> dict:
        return asdict(self)
