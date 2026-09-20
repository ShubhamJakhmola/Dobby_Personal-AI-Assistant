from __future__ import annotations

import threading
from dataclasses import asdict
from datetime import datetime, timezone

from brain.models import ProviderUsage


class UsageTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._items: list[dict] = []

    def record(self, response, task_type: str = "") -> dict:
        usage = response.usage or {}
        actual = bool(usage.get("usage_available", False))
        input_tokens = int(usage.get("input_tokens", 0) or 0) if actual else 0
        output_tokens = int(usage.get("output_tokens", 0) or 0) if actual else 0
        item = ProviderUsage(response.provider, response.model, 1, input_tokens, output_tokens,
                             input_tokens + output_tokens, actual,
                             0 if actual else self.estimate(response.metadata.get("request_text", "")),
                             0 if actual else self.estimate(response.content), task_type).as_dict()
        item["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._items.append(item)
        return item

    @staticmethod
    def estimate(text: str) -> int:
        return max(0, (len(str(text)) + 3) // 4)

    def summary(self) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._items]