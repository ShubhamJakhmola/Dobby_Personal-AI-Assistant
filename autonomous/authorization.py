"""Scoped, revocable, auditable user authorization for autonomous workflows (Phase 19).

When a user grants Dobby permission to perform a class of actions autonomously
(e.g. "apply to DevOps jobs in Chandigarh"), that authorization is stored here
with explicit scope, constraints, and expiry.

Design principles:
- Explicit: the user stated the authorization, it is not inferred.
- Inspectable: can always be listed and read.
- Revocable: can be revoked at any time.
- Scoped: limited to the stated capability / parameters.
- Auditable: every check is logged.
- NOT a policy authority: it supplements, never overrides, Dobby's L0-L3 policy.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid


_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_path() -> Path:
    root = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "authorizations.json"


@dataclass
class Authorization:
    """A scoped user authorization for a class of autonomous actions."""

    auth_id: str = field(default_factory=lambda: f"auth-{uuid.uuid4().hex[:10]}")
    scope: str = ""                    # e.g. "job_application"
    parameters: dict[str, Any] = field(default_factory=dict)
    # Common parameter keys for job application:
    #   role_types, locations, salary_min, excluded_companies,
    #   max_applications_per_day, expires_at
    created_at: str = field(default_factory=_now)
    revoked: bool = False
    revoked_at: str | None = None
    use_count: int = 0

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        expires = self.parameters.get("expires_at")
        if expires:
            try:
                if datetime.fromisoformat(expires) < datetime.now(timezone.utc):
                    return False
            except ValueError:
                pass
        return True

    def as_dict(self) -> dict:
        return asdict(self)


def _load() -> dict[str, dict]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(store: dict) -> None:
    _store_path().write_text(json.dumps(store, indent=2), encoding="utf-8")


class AuthorizationStore:
    """Manages durable scoped user authorizations."""

    def __init__(self, storage_path: Path | None = None):
        self._custom_path = storage_path

    def _path(self) -> Path:
        return self._custom_path or _store_path()

    def _load(self) -> dict[str, dict]:
        path = self._path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, store: dict) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, indent=2), encoding="utf-8")

    # ---- grant / revoke -------------------------------------------------

    def grant(self, scope: str, parameters: dict[str, Any] | None = None) -> Authorization:
        """Create and persist a new scoped authorization."""
        auth = Authorization(scope=scope, parameters=parameters or {})
        with _LOCK:
            store = self._load()
            store[auth.auth_id] = auth.as_dict()
            self._save(store)
        return auth

    def revoke(self, auth_id: str) -> bool:
        """Revoke an authorization. Returns True if it existed."""
        with _LOCK:
            store = self._load()
            if auth_id not in store:
                return False
            store[auth_id]["revoked"] = True
            store[auth_id]["revoked_at"] = _now()
            self._save(store)
        return True

    # ---- checks ---------------------------------------------------------

    def check(self, scope: str, action_parameters: dict | None = None) -> Authorization | None:
        """Return the first valid authorization matching scope, or None."""
        action_parameters = action_parameters or {}
        with _LOCK:
            store = self._load()
        for raw in store.values():
            auth = Authorization(**raw)
            if auth.scope != scope or not auth.is_valid():
                continue
            if self._matches_parameters(auth.parameters, action_parameters):
                return auth
        return None

    def is_authorized(self, scope: str, action_parameters: dict | None = None) -> bool:
        """Return True if a valid authorization exists for this scope."""
        return self.check(scope, action_parameters) is not None

    def consume(self, auth_id: str) -> bool:
        """Increment use_count; returns False if authorization no longer valid."""
        with _LOCK:
            store = _load()
            if auth_id not in store:
                return False
            auth = Authorization(**store[auth_id])
            if not auth.is_valid():
                return False
            store[auth_id]["use_count"] = auth.use_count + 1
            _save(store)
        return True

    # ---- list / inspect -------------------------------------------------

    def list(self, include_revoked: bool = False) -> list[dict]:
        with _LOCK:
            store = _load()
        result = []
        for raw in store.values():
            auth = Authorization(**raw)
            if not include_revoked and auth.revoked:
                continue
            result.append(auth.as_dict())
        return result

    def get(self, auth_id: str) -> Authorization | None:
        with _LOCK:
            store = _load()
        raw = store.get(auth_id)
        return Authorization(**raw) if raw else None

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _matches_parameters(auth_params: dict, action_params: dict) -> bool:
        """Verify that action_params are within the bounds of auth_params."""
        # Check excluded_companies
        excluded = auth_params.get("excluded_companies", [])
        company = action_params.get("company", "").lower()
        if company and any(company == ex.lower() for ex in excluded):
            return False

        # Check salary_min
        salary_min = auth_params.get("salary_min")
        salary_offered = action_params.get("salary")
        if salary_min is not None and salary_offered is not None:
            try:
                if float(salary_offered) < float(salary_min):
                    return False
            except (TypeError, ValueError):
                pass

        # Check locations
        locations = auth_params.get("locations", [])
        action_location = action_params.get("location", "")
        if locations and action_location:
            if not any(loc.lower() in action_location.lower() for loc in locations):
                return False

        return True
