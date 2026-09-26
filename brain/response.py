from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BrainResponse:
    provider: str
    model: str
    status: str
    content: str = ""
    structured_data: dict | None = None
    usage: dict = field(default_factory=dict)
    duration: float = 0.0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)