from __future__ import annotations

import json
import socket
import threading
import time

from remote.device_registry import DeviceRegistry
from remote.models import RemoteTask
from remote.protocol import RemoteProtocol
from remote.transports.tls import TLSConfig


class LinuxRemoteClient:
    def __init__(self, core_host: str = "127.0.0.1", core_port: int = 8765, cert_file: str | None = None,
                 secure_mode: str = "development", device_name: str = "linux-client", registry: DeviceRegistry | None = None):
        self.core_host = core_host
        self.core_port = core_port
        self.device_id = device_name
        self.secure_mode = secure_mode
        self.registry = registry or DeviceRegistry()
        self.tls = TLSConfig(enabled=bool(cert_file), verify_cert=False, secure_mode=secure_mode, cert_file=cert_file or "")
        self.online = False
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = False

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.core_host, self.core_port))
        self.online = True
        self._sock.sendall(json.dumps({"device_id": self.device_id, "type": "hello"}).encode("utf-8"))
        response = self._sock.recv(4096)
        return json.loads(response.decode("utf-8"))

    def capabilities(self):
        return ["process", "filesystem", "terminal"]

    def perform_task(self, task: RemoteTask):
        if not self.online or self._sock is None:
            return {"status": "BLOCKED", "reason": "offline"}
        payload = RemoteProtocol().encode_task(task)
        envelope = {"type": "task", "payload": payload}
        self._sock.sendall(json.dumps(envelope).encode("utf-8"))
        try:
            response = self._sock.recv(4096)
        except OSError:
            return {"status": "BLOCKED", "reason": "socket_error"}
        return json.loads(response.decode("utf-8"))

    def stop(self):
        self.online = False
        self._stop = True
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
