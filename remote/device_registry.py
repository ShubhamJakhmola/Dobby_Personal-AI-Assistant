from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from remote.models import DeviceIdentity, DeviceSession, DeviceState


class DeviceRegistry:
    def __init__(self, path: str | Path | None = None):
        raw = Path(path) if path is not None else Path.home() / ".dobby" / "devices.json"
        if raw.exists() and raw.is_dir():
            self.path = raw / "devices.json"
        else:
            self.path = raw if raw.suffix else raw / "devices.json"
        self._devices: dict[str, dict] = {}
        self._sessions: dict[str, DeviceSession] = {}
        self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if isinstance(data, dict):
            self._devices = data.get("devices", {})

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"devices": self._devices}, indent=2), encoding="utf-8")

    def enroll(self, identity: DeviceIdentity, session: DeviceSession | None = None) -> dict:
        record = {
            "device_id": identity.device_id,
            "device_name": identity.device_name,
            "platform": identity.platform,
            "architecture": identity.architecture,
            "client_version": identity.client_version,
            "state": DeviceState.AUTHENTICATED.value,
            "capabilities": [],
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "metadata": identity.metadata,
            "public_identity": identity.public_key,
            "authorization": "device:basic",
            "status": DeviceState.AUTHENTICATED.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._devices[identity.device_id] = record
        self._save()
        if session:
            self._sessions[identity.device_id] = session
        return record

    def get(self, device_id: str) -> dict | None:
        return self._devices.get(device_id)

    def list(self) -> list[dict]:
        return list(self._devices.values())

    def online(self) -> list[dict]:
        return [device for device in self.list() if device.get("state") == DeviceState.ONLINE.value]

    def update_capabilities(self, device_id: str, capabilities: list[dict]) -> None:
        device = self._devices.get(device_id)
        if not device:
            return
        device["capabilities"] = capabilities
        device["last_seen"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def revoke(self, device_id: str) -> dict:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "device_id": device_id}
        device["state"] = DeviceState.REVOKED.value
        self._save()
        return {"success": True, "device_id": device_id, "state": device["state"]}

    def status(self) -> dict:
        devices = self.list()
        return {"total": len(devices), "online": len(self.online()), "offline": sum(1 for d in devices if d.get("state") == DeviceState.OFFLINE.value),
                "revoked": sum(1 for d in devices if d.get("state") == DeviceState.REVOKED.value), "devices": devices,
                "security_mode": "development", "tls_state": "not_configured"}

    def select_for_task(self, task, *, required_capability: str | None = None, preferred_platform: str | None = None) -> dict | None:
        required = required_capability or getattr(task, "capability", None)
        candidates = [device for device in self.list() if device.get("state") in {DeviceState.ONLINE.value, DeviceState.AUTHENTICATED.value, "ONLINE", "AUTHENTICATED"}]
        if preferred_platform:
            candidates = [device for device in candidates if str(device.get("platform", "")).lower() == str(preferred_platform).lower()]
        ordered = sorted(candidates, key=lambda d: (d.get("device_id") or ""))
        for device in ordered:
            caps = []
            for item in device.get("capabilities", []):
                if isinstance(item, dict):
                    caps.append(item.get("id") or item.get("name"))
                else:
                    caps.append(str(item))
            if required in caps:
                return device
        return None


def make_device_identity(name: str, platform: str = "linux", architecture: str = "x86_64", version: str = "0.1.0") -> DeviceIdentity:
    device_id = uuid.uuid4().hex
    return DeviceIdentity(device_id, name, platform, architecture, version, metadata={"generated": True})
