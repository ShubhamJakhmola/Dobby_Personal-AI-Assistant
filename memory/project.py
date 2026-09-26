from __future__ import annotations

from pathlib import Path

from memory.models import ProjectContext, timestamp
from memory.storage import memory_root, read_json, write_json


class ProjectContextStore:
    def __init__(self, root=None):
        self.path = memory_root(root) / "projects.json"

    def get(self, name: str) -> dict | None:
        return read_json(self.path, {}).get(name)

    def upsert(self, name: str, **values) -> dict:
        data = read_json(self.path, {})
        current = {**ProjectContext(name).as_dict(), **(data.get(name) or {})}
        for key, value in values.items():
            if key in current: current[key] = value
        current["updated_at"] = timestamp()
        data[name] = current
        write_json(self.path, data)
        return current

    def list(self) -> list[dict]:
        return list(read_json(self.path, {}).values())