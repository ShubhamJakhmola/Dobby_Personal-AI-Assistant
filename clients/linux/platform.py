from __future__ import annotations

from clients.base import ClientRuntime


class LinuxClientPlatform(ClientRuntime):
    def __init__(self):
        super().__init__(name="linux-client", platform="linux", capabilities=["terminal", "filesystem", "process", "systemd"])
