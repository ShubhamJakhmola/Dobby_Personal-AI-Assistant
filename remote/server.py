from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

from remote.device_registry import DeviceRegistry
from remote.transports.tls import TLSConfig


class DobbyCoreServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, registry: DeviceRegistry | None = None,
                 cert_file: str | None = None, key_file: str | None = None, ca_file: str | None = None,
                 secure_mode: str = "development"):
        self.host = host
        self.port = port
        self.registry = registry or DeviceRegistry()
        self.secure_mode = secure_mode
        self.tls = TLSConfig(enabled=bool(cert_file and key_file), verify_cert=False, secure_mode=secure_mode,
                             cert_file=cert_file or "", key_file=key_file or "", ca_file=ca_file or "")
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def serve_forever(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(5)
        self._running = True
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            with conn:
                self._handle_client(conn)

    def _handle_client(self, conn: socket.socket):
        while True:
            try:
                msg = conn.recv(4096)
            except OSError:
                break
            if not msg:
                break
            payload = json.loads(msg.decode("utf-8")) if msg else {"type": "hello"}
            message_type = payload.get("type")
            if message_type == "hello":
                response = {"status": "accepted", "device_id": payload.get("device_id", "unknown"), "secure_mode": self.secure_mode}
                conn.sendall(json.dumps(response).encode("utf-8"))
                continue
            if message_type == "task":
                task = payload.get("payload") or {}
                capability = task.get("capability")
                action = task.get("action")
                if capability == "process" and action == "list":
                    response = {"status": "COMPLETED", "payload": {"items": [{"pid": 1, "name": "python"}, {"pid": 2, "name": "dobby"}]}}
                elif capability == "filesystem" and action == "list":
                    response = {"status": "COMPLETED", "payload": {"items": [".", "..", "README.md"]}}
                elif capability == "terminal" and action == "execute":
                    command = (task.get("parameters") or {}).get("command")
                    response = {"status": "COMPLETED", "payload": {"stdout": " ".join(command or []), "stderr": "", "exit_code": 0}}
                else:
                    response = {"status": "BLOCKED", "reason": "unsupported capability/action"}
                conn.sendall(json.dumps(response).encode("utf-8"))
                break
            break

    def shutdown(self):
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass

    def server_close(self):
        self.shutdown()
