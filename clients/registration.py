from __future__ import annotations

from remote.device_registry import DeviceRegistry


class ClientRegistry:
    def __init__(self, device_registry: DeviceRegistry | None = None):
        self.device_registry = device_registry or DeviceRegistry()

    def list(self) -> list[dict]:
        return self.device_registry.list()

    def register(self, identity, session=None) -> dict:
        return self.device_registry.enroll(identity, session)
