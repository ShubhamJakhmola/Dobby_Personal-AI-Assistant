"""Small local library for user-taught workflows/skills.

These are procedures Dobby can retrieve and reason over; they are not executable
code. Promotion to an executable adapter still goes through the acquisition and
security pipeline.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()


def _path() -> Path:
    root = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "taught_skills.json"


def _load() -> list[dict]:
    p = _path()
    if not p.exists():
        return []
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def save_skill(name: str, trigger: str, steps: list[str], notes: str = "") -> dict:
    entry = {
        "name": name.strip(),
        "trigger": trigger.strip(),
        "steps": [str(x).strip() for x in steps if str(x).strip()],
        "notes": notes.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "learned_procedure",
    }
    with _LOCK:
        rows = _load()
        rows = [x for x in rows if str(x.get("name", "")).lower() != entry["name"].lower()]
        rows.append(entry)
        _path().write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry


def list_skills() -> list[dict]:
    return _load()


def find_skill(query: str, limit: int = 5) -> list[dict]:
    q = query.lower().strip()
    rows = _load()
    if not q:
        return rows[:limit]
    scored = []
    for row in rows:
        hay = " ".join([str(row.get("name", "")), str(row.get("trigger", "")), str(row.get("notes", "")), " ".join(row.get("steps", []))]).lower()
        score = sum(1 for token in q.split() if token in hay)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:limit]]
