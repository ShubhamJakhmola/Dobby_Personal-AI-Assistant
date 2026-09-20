from __future__ import annotations

from typing import Protocol


class BrowserAdapter(Protocol):
    def status(self) -> dict:
        ...

    def open(self, url: str) -> dict:
        ...