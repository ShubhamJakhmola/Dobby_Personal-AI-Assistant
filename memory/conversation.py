from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from memory.models import ConversationEntry
from memory.policy import sanitize
from memory.storage import memory_root


class ConversationManager:
    def __init__(self, root: str | Path | None = None):
        self.root = memory_root(root) / "conversations"

    def _path(self, when=None) -> Path:
        date = when or datetime.now(timezone.utc)
        return self.root / date.strftime("%Y") / f"{date:%Y-%m-%d}.jsonl"

    def append(self, role: str, message: str, **metadata) -> dict:
        safe = sanitize(message)
        entry = ConversationEntry(role=role, message=safe,
                                  task=str(metadata.pop("task", "")),
                                  project=str(metadata.pop("project", "")), metadata=metadata)
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry.as_dict(), ensure_ascii=False) + "\n")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return entry.as_dict()

    def recent(self, limit: int = 10) -> list[dict]:
        files = sorted(self.root.glob("**/*.jsonl"), reverse=True)
        entries = []
        for path in files:
            for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(entries) >= max(0, limit):
                    return list(reversed(entries))
        return list(reversed(entries))

    def search(self, query: str, limit: int = 10) -> list[dict]:
        terms = set(query.lower().split())
        return [entry for entry in self.recent(500)
                if terms & set(str(entry.get("message", "")).lower().split())][:limit]