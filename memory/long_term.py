from __future__ import annotations

import uuid
from pathlib import Path

from memory.models import MemoryRecord, timestamp
from memory.policy import is_sensitive, sanitize
from memory.storage import memory_root, read_json, write_json


class LongTermMemory:
    def __init__(self, root: str | Path | None = None):
        self.path = memory_root(root) / "long_term_records.json"

    def _records(self) -> list[dict]:
        raw = read_json(self.path, [])
        return raw if isinstance(raw, list) else []

    def remember(self, category: str, key: str, value: str, **metadata) -> dict:
        if is_sensitive(value) or is_sensitive(key):
            raise ValueError("secret-like values cannot be stored in long-term memory")
        records = self._records()
        existing = next((item for item in records if item.get("category") == category and item.get("key") == key), None)
        now = timestamp()
        if existing:
            existing.update(value=sanitize(value), updated_at=now, **{k: v for k, v in metadata.items() if k in {"confidence", "source", "topic", "project", "task"}})
            record = existing
        else:
            record = MemoryRecord(str(uuid.uuid4()), category, key, sanitize(value), **{k: v for k, v in metadata.items() if k in {"confidence", "source", "topic", "project", "task"}}).as_dict()
            records.append(record)
        write_json(self.path, records)
        return record

    def update(self, record_id: str, **values) -> dict | None:
        records = self._records()
        target = next((item for item in records if item.get("id") == record_id), None)
        if not target:
            return None
        if "value" in values and is_sensitive(values["value"]):
            raise ValueError("secret-like values cannot be stored in long-term memory")
        for key, value in values.items():
            if key in {"category", "key", "value", "confidence", "source", "topic", "project", "task"}:
                target[key] = sanitize(value) if key == "value" else value
        target["updated_at"] = timestamp()
        write_json(self.path, records)
        return target

    def get(self, record_id: str) -> dict | None:
        return next((item for item in self._records() if item.get("id") == record_id), None)

    def search(self, query: str = "", *, topic: str = "", project: str = "", task: str = "", limit: int = 10) -> list[dict]:
        terms = set(query.lower().split())
        result = []
        for item in self._records():
            if project and item.get("project") and item.get("project").lower() != project.lower():
                continue
            if topic and item.get("topic") and item.get("topic").lower() != topic.lower():
                continue
            text = " ".join(str(item.get(field, "")) for field in ("category", "key", "value", "topic", "project", "task")).lower()
            score = len(terms & set(text.split()))
            if topic and topic.lower() in text: score += 3
            if project and project.lower() in text: score += 4
            item = {**item, "relevance": score}
            if score or not terms:
                result.append(item)
        result.sort(key=lambda item: (item["relevance"], item.get("updated_at", "")), reverse=True)
        return result[:max(0, limit)]

    def delete(self, record_id: str) -> bool:
        records = self._records()
        remaining = [item for item in records if item.get("id") != record_id]
        changed = len(remaining) != len(records)
        if changed: write_json(self.path, remaining)
        return changed

    def clear(self) -> None:
        write_json(self.path, [])