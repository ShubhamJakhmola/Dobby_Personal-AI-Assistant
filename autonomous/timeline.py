"""Task timeline event logger for the autonomous engine (Phase 19).

Records a structured event for every significant state transition in
a goal's lifecycle.  Events are appended to a JSONL file alongside
the main audit log and are visible through the CLI / dashboard.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TimelineEvent(str, Enum):
    GOAL_CREATED = "GOAL_CREATED"
    PLAN_CREATED = "PLAN_CREATED"
    STEP_STARTED = "STEP_STARTED"
    CAPABILITY_SELECTED = "CAPABILITY_SELECTED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFIED = "VERIFIED"
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    WAITING = "WAITING"
    GOAL_COMPLETED = "GOAL_COMPLETED"
    GOAL_FAILED = "GOAL_FAILED"
    GOAL_CANCELLED = "GOAL_CANCELLED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_STRATEGY = "RECOVERY_STRATEGY"


_LOCK = threading.Lock()


def _timeline_path() -> Path:
    root = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "timeline.jsonl"


def record(goal_id: str, event: TimelineEvent, metadata: dict[str, Any] | None = None) -> dict:
    """Append a timeline entry and return it."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "goal_id": goal_id,
        "event": event.value,
        **(metadata or {}),
    }
    with _LOCK:
        with _timeline_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return entry


def recent_for_goal(goal_id: str, limit: int = 50) -> list[dict]:
    """Return most-recent timeline entries for a specific goal."""
    path = _timeline_path()
    if not path.exists():
        return []
    results = []
    with _LOCK:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("goal_id") == goal_id:
                    results.append(entry)
            except json.JSONDecodeError:
                pass
    return results[-limit:]


def recent(limit: int = 100) -> list[dict]:
    """Return most-recent timeline entries across all goals."""
    path = _timeline_path()
    if not path.exists():
        return []
    with _LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out[-limit:]


class TaskTimeline:
    """Per-goal timeline convenience wrapper."""

    def __init__(self, goal_id: str):
        self.goal_id = goal_id

    def emit(self, event: TimelineEvent, **kwargs: Any) -> dict:
        return record(self.goal_id, event, kwargs or None)

    def history(self, limit: int = 50) -> list[dict]:
        return recent_for_goal(self.goal_id, limit)
