from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class FakeTransport:
    connected: bool = False
    messages: list[dict] = None
    reconnect_count: int = 0

    def __post_init__(self):
        if self.messages is None:
            self.messages = []

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True

    def send(self, message: dict):
        if not self.connected:
            raise RuntimeError("transport not connected")
        self.messages.append(message)
        return True

    def receive(self):
        if not self.messages:
            return None
        return self.messages.pop(0)

    def reconnect(self):
        self.reconnect_count += 1
        self.connected = True
        return True


class RemoteConnection:
    def __init__(self, transport=None):
        self.transport = transport or FakeTransport()
        self.connected = False
        self.last_seen = 0.0

    def connect(self):
        self.connected = self.transport.connect()
        self.last_seen = time.time()
        return self.connected

    def disconnect(self):
        self.connected = not self.transport.disconnect()
        self.last_seen = time.time()
        return True

    def send(self, message: dict):
        self.transport.send(message)
        self.last_seen = time.time()
        return True

    def receive(self):
        item = self.transport.receive()
        if item is not None:
            self.last_seen = time.time()
        return item
