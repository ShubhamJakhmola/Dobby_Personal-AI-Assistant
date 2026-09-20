from __future__ import annotations

from typing import Protocol


class Scheduler(Protocol):
    def list(self) -> dict[str, dict]:
        ...

    def verify(self, name: str, schedule: str | None = None, command: list[str] | None = None) -> bool:
        ...