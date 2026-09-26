from __future__ import annotations

from clients.base import ClientRuntime


class LocalClientRuntime(ClientRuntime):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
