from __future__ import annotations

from remote.connection import RemoteConnection


class ClientTransport:
    def __init__(self, connection: RemoteConnection | None = None):
        self.connection = connection or RemoteConnection()

    def connect(self):
        return self.connection.connect()

    def disconnect(self):
        return self.connection.disconnect()

    def send(self, message: dict):
        return self.connection.send(message)

    def receive(self):
        return self.connection.receive()
