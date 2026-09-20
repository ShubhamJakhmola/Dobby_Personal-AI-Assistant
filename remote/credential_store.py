from __future__ import annotations

import json
import os
from pathlib import Path


class CredentialStore:
    def __init__(self, path: str | None = None, *, development_mode: bool = False):
        self.path = Path(path or os.path.join(os.path.expanduser("~"), ".dobby", "credentials.json"))
        self.development_mode = development_mode
        self._data: dict = {}
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def state(self) -> str:
        return "DEVELOPMENT_ONLY" if self.development_mode else "AVAILABLE"

    def save_identity(self, identity):
        self._data[identity.device_id] = {"device_id": identity.device_id, "device_name": identity.device_name, "platform": identity.platform, "architecture": identity.architecture, "client_version": identity.client_version, "public_key": identity.public_key, "private_key": identity.private_key}
        self._save()

    def load_identity(self, device_id: str):
        return self._data.get(device_id)
