from __future__ import annotations

import json
from pathlib import Path

from memory.storage import memory_root, read_json, write_json


class AgentPersistence:
    def __init__(self, root=None):
        self.path = memory_root(root) / "agents.json"

    def load(self) -> dict:
        value = read_json(self.path, {})
        return value if isinstance(value, dict) else {}

    def save(self, spec) -> None:
        data = self.load(); data[spec.agent_id] = spec.as_dict(); write_json(self.path, data)

    def delete(self, agent_id: str) -> None:
        data = self.load(); data.pop(agent_id, None); write_json(self.path, data)