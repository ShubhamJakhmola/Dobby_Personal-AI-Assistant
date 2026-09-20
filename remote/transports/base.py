from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MessageEnvelope:
    protocol_version: str = "1.0"
    message_id: str = ""
    message_type: str = ""
    timestamp: str = ""
    device_id: str = ""
    correlation_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "protocol_version": self.protocol_version,
            "message_id": self.message_id,
            "message_type": self.message_type,
            "timestamp": self.timestamp or str(time.time()),
            "device_id": self.device_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }


class BaseTransport:
    def __init__(self, *, secure_mode: str = "development", tls_enabled: bool = False):
        self.secure_mode = secure_mode
        self.tls_enabled = tls_enabled
        self.connected = False
        self.last_seen = 0.0

    def connect(self):
        self.connected = True
        self.last_seen = time.time()
        return True

    def disconnect(self):
        self.connected = False
        self.last_seen = time.time()
        return True

    def send(self, message: dict):
        raise NotImplementedError

    def receive(self):
        raise NotImplementedError


class ProductionTransport(BaseTransport):
    def __init__(self, *, secure_mode: str = "development", tls_enabled: bool = False, endpoint: str = "ws://localhost"):
        super().__init__(secure_mode=secure_mode, tls_enabled=tls_enabled)
        self.endpoint = endpoint

    def send(self, message: dict):
        return {"sent": True, "endpoint": self.endpoint, "secure_mode": self.secure_mode, "payload": message}

    def receive(self):
        return {"status": "no_message", "secure_mode": self.secure_mode}
