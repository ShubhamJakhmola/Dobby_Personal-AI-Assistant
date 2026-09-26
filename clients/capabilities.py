from __future__ import annotations


class ClientCapabilities:
    def __init__(self, **capabilities):
        self._capabilities = capabilities

    def has(self, capability: str) -> bool:
        return capability in self._capabilities and bool(self._capabilities[capability])

    def manifest(self) -> list[dict]:
        return [{"id": key, "version": "1"} for key, value in self._capabilities.items() if value]
