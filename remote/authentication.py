from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass


@dataclass
class EnrollmentToken:
    token: str
    device_id: str
    created_at: float
    expires_at: float
    used: bool = False

    def valid_for(self, device_id: str) -> bool:
        return not self.used and self.device_id == device_id and time.time() < self.expires_at


class DeviceAuthenticator:
    def __init__(self):
        self._tokens: dict[str, EnrollmentToken] = {}
        self._nonces: dict[str, str] = {}

    def create_enrollment_token(self, device_id: str, ttl_seconds: int = 900) -> EnrollmentToken:
        token = hashlib.sha256(f"{device_id}:{secrets.token_hex(16)}:{time.time()}".encode("utf-8")).hexdigest()
        entry = EnrollmentToken(token, device_id, time.time(), time.time() + ttl_seconds)
        self._tokens[token] = entry
        return entry

    def verify_enrollment(self, device_id: str, token: str) -> bool:
        entry = self._tokens.get(token)
        if not entry:
            return False
        if entry.valid_for(device_id):
            entry.used = True
            return True
        return False

    def issue_identity(self, device_id: str, device_name: str, platform: str, arch: str, version: str) -> dict:
        public = hashlib.sha256(f"{device_id}:{device_name}:{platform}:{arch}:{version}".encode("utf-8")).hexdigest()
        private = hashlib.sha256(f"device-private:{device_id}:{secrets.token_hex(16)}".encode("utf-8")).hexdigest()
        return {"public_key": public, "private_key": private}

    def create_challenge(self, device_id: str) -> str:
        challenge = hashlib.sha256(f"challenge:{device_id}:{secrets.token_hex(16)}".encode("utf-8")).hexdigest()
        self._nonces[device_id] = challenge
        return challenge

    def sign_challenge(self, challenge: str, device_id: str) -> str:
        return hashlib.sha256(f"{challenge}:{device_id}".encode("utf-8")).hexdigest()

    def verify_challenge(self, device_id: str, challenge: str, proof: str) -> bool:
        expected = self._nonces.get(device_id)
        if not expected or expected != challenge:
            return False
        return hashlib.sha256(f"{challenge}:{device_id}".encode("utf-8")).hexdigest() == proof
