from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


class BrainRole:
    MASTER = "master"
    SPECIALIST = "specialist"


@dataclass
class BrainProfile:
    provider_id: str
    model_id: str
    role: str = BrainRole.SPECIALIST
    capabilities: list[str] = field(default_factory=list)
    reasoning_level: str = "medium"
    context_capacity: int = 6000
    structured_output: bool = True
    privacy: str = "external_api"
    configured: bool = False
    available: bool = False
    explanation: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProviderHealth:
    available: bool
    status: str
    reason: str = ""


@dataclass
class ProviderUsage:
    provider: str
    model: str
    request_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    usage_available: bool = False
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    task_type: str = ""

    def as_dict(self) -> dict:
        return asdict(self)