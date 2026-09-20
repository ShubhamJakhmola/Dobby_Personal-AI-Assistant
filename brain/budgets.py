from __future__ import annotations

from datetime import date


class BudgetManager:
    def __init__(self, limits: dict | None = None):
        self.limits = limits or {}
        self._usage: dict[str, dict] = {}

    def check(self, provider: str, estimated_tokens: int = 0) -> tuple[bool, str]:
        limit = self.limits.get(provider, {})
        used = self._usage.get(provider, {"requests": 0, "tokens": 0})
        request_limit = limit.get("daily_request_limit")
        token_limit = limit.get("daily_token_limit")
        if request_limit is not None and used["requests"] >= request_limit:
            return False, "daily request limit reached"
        if token_limit is not None and used["tokens"] + estimated_tokens > token_limit:
            return False, "daily estimated token limit reached"
        return True, "within internal budget"

    def record(self, provider: str, estimated_tokens: int = 0) -> None:
        usage = self._usage.setdefault(provider, {"requests": 0, "tokens": 0})
        usage["requests"] += 1
        usage["tokens"] += max(0, estimated_tokens)

    def status(self) -> dict:
        return {"limits": self.limits, "usage": self._usage.copy(), "scope": "Dobby internal only"}