from __future__ import annotations

from clients.base import ClientRuntime


class WindowsClientPlatform(ClientRuntime):
    def __init__(self):
        super().__init__(name="windows-client", platform="windows", capabilities=["terminal", "powershell", "filesystem", "process", "applications"])
