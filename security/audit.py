"""Append-only local audit records with basic secret redaction."""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,}]+")


def audit_path() -> Path:
    root = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "audit.jsonl"


def _redact(value):
    if isinstance(value, str):
        return _SECRET.sub(r"\1=[REDACTED]", value)
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if any(token in str(key).lower()
                           for token in ("api_key", "apikey", "token", "password", "secret"))
                  else _redact(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def record(**fields) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **_redact(fields)}
    with _LOCK:
        with audit_path().open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=True) + "\n")


def recent(limit: int = 20) -> list[dict]:
    path = audit_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-max(1, int(limit)):]
    return [json.loads(line) for line in lines if line.strip()]