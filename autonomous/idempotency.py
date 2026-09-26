"""Idempotency store — prevents duplicate external actions on retry (Phase 19).

Before executing any external action (email, job application, message,
calendar event, ticket, etc.) the AutonomousExecutor checks this store.
If a matching completed action exists, the execution is skipped and the
prior result is returned instead.

Storage: append-to-dict JSON file at ~/.dobby/idempotency.json
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOCK = threading.Lock()


def _store_path() -> Path:
    root = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "idempotency.json"


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


class IdempotencyStore:
    """Thread-safe store for external action deduplication."""

    def __init__(self, storage_path: Path | None = None):
        self._custom_path = storage_path

    def _path(self) -> Path:
        return self._custom_path or _store_path()

    def check(self, idempotency_key: str) -> dict | None:
        """Return the stored result if the key was already executed, else None."""
        if not idempotency_key:
            return None
        with _LOCK:
            path = self._path()
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data.get(idempotency_key)
            except Exception:
                return None

    def record(
        self,
        idempotency_key: str,
        action: str,
        target: str,
        result: Any,
        external_reference: str = "",
    ) -> dict:
        """Persist a completed external action so it is never re-executed."""
        if not idempotency_key:
            return {}
        if hasattr(result, "as_dict"):
            res_data = result.as_dict()
        elif isinstance(result, dict):
            res_data = result
        else:
            res_data = str(result)
        entry = {
            "idempotency_key": idempotency_key,
            "action": action,
            "target": target,
            "result": res_data,
            "external_reference": external_reference,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with _LOCK:
            path = self._path()
            store = {}
            if path.exists():
                try:
                    store = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            store[idempotency_key] = entry
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(store, indent=2), encoding="utf-8")
        return entry

    def was_executed(self, idempotency_key: str) -> bool:
        """True if the key is already in the store (action completed previously)."""
        return self.check(idempotency_key) is not None

    def clear(self, idempotency_key: str) -> bool:
        """Remove a key (e.g. to allow a retry after a confirmed partial failure)."""
        with _LOCK:
            store = _load()
            if idempotency_key in store:
                del store[idempotency_key]
                _save(store)
                return True
        return False

    def list_all(self) -> list[dict]:
        """Return all recorded external actions."""
        with _LOCK:
            return list(_load().values())
