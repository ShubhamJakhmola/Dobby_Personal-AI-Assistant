from __future__ import annotations

from remote.models import RemoteTask, RemoteTaskResult


class RemoteProtocol:
    def __init__(self, version: str = "1.0"):
        self.version = version

    def envelope(self, message_type: str, payload: dict, *, device_id: str = "", correlation_id: str = "") -> dict:
        return {"protocol_version": self.version, "message_type": message_type, "device_id": device_id,
                "correlation_id": correlation_id or payload.get("task_id") or "", "payload": payload}

    def validate(self, message: dict) -> bool:
        required = {"task_id", "device_id", "capability", "action"}
        if isinstance(message, dict):
            if required.issubset(message.keys()):
                return True
            return required.issubset((message.get("payload") or {}).keys())
        return False

    def encode_task(self, task: RemoteTask) -> dict:
        return task.as_dict()

    def decode_task(self, message: dict) -> RemoteTask:
        payload = message.get("payload", message)
        return RemoteTask(**payload)

    def encode_result(self, result: RemoteTaskResult) -> dict:
        return result.as_dict()

    def decode_result(self, message: dict) -> RemoteTaskResult:
        return RemoteTaskResult(**(message.get("payload", message)))

    def validate_envelope(self, envelope: dict) -> bool:
        if not isinstance(envelope, dict):
            return False
        if str(envelope.get("protocol_version", "")).strip() == "":
            return False
        if not envelope.get("message_type"):
            return False
        if not isinstance(envelope.get("payload", {}), dict):
            return False
        return True
