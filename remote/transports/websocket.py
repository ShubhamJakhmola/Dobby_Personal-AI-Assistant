from __future__ import annotations

from remote.transports.base import BaseTransport


class WebSocketTransport(BaseTransport):
    def __init__(self, *, secure_mode: str = "development", tls_enabled: bool = False, endpoint: str = "ws://localhost"):
        super().__init__(secure_mode=secure_mode, tls_enabled=tls_enabled)
        self.endpoint = endpoint

    def send(self, message: dict):
        return {"sent": True, "transport": "websocket", "endpoint": self.endpoint, "secure_mode": self.secure_mode, "message": message}

    def receive(self):
        return {"status": "no_message", "transport": "websocket", "secure_mode": self.secure_mode}
