from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from memory.models import ContextState, timestamp
from memory.storage import memory_root, read_json, write_json


class ContextManager:
    def __init__(self, root: str | Path | None = None):
        self.path = memory_root(root) / "context.json"

    def get_current(self) -> dict:
        raw = read_json(self.path, {})
        return {**ContextState().as_dict(), **raw} if isinstance(raw, dict) else ContextState().as_dict()

    def update(self, **values) -> dict:
        current = self.get_current()
        for key, value in values.items():
            if key in current and value is not None:
                current[key] = value
        current["updated_at"] = timestamp()
        write_json(self.path, current)
        return current

    def clear(self) -> dict:
        state = ContextState().as_dict()
        write_json(self.path, state)
        return state

    def set_topic(self, topic: str) -> dict:
        return self.update(topic=topic, recent_intent="")

    def set_task(self, task: str) -> dict:
        return self.update(active_task=task)

    def set_project(self, project: str) -> dict:
        return self.update(project=project)