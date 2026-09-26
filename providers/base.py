from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    """The small contract the orchestration layer needs from an AI brain."""

    def text(self, prompt: str, *, system: str = "", timeout_ms: int = 10000) -> str:
        ...