from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrainRequest:
    task: str
    task_type: str = "general"
    complexity: str = "medium"
    required_capabilities: list[str] = field(default_factory=list)
    context_packet: dict | None = None
    context_requirements: dict = field(default_factory=dict)
    privacy_level: str = "any"
    latency_requirement: str = "normal"
    max_context: int = 6000
    max_output: int = 1000
    structured_output_required: bool = False
    preferred_provider: str = ""
    excluded_providers: list[str] = field(default_factory=list)
    role: str = "specialist"
    metadata: dict[str, Any] = field(default_factory=dict)