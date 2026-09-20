from __future__ import annotations

import time

from brain.budgets import BudgetManager
from brain.context import BrainContextBroker
from brain.models import BrainRole
from brain.policies import privacy_allowed, profile_matches
from brain.response import BrainResponse
from brain.usage import UsageTracker


class BrainRouter:
    """Deliberate provider selection. Provider failure is never an implicit fallback."""
    def __init__(self, registry, *, master_provider="gemini", context_broker=None,
                 usage=None, budgets=None):
        self.registry = registry
        self.master_provider = master_provider
        self.context = context_broker or BrainContextBroker()
        self.usage = usage or UsageTracker()
        self.budgets = budgets or BudgetManager()

    def route(self, request, *, dry_run=False) -> dict:
        candidates = []
        for profile in self.registry.list():
            if profile["provider_id"] in request.excluded_providers:
                continue
            provider = self.registry.get(profile["provider_id"])
            health = provider.health_check()
            if not health.available:
                continue
            if request.role == BrainRole.MASTER and profile["provider_id"] != self.master_provider:
                continue
            ok, reason = profile_matches(provider.profile, request)
            if not ok:
                continue
            capability_reason = reason
            ok, reason = privacy_allowed(provider.profile, request)
            if not ok:
                continue
            budget_ok, budget_reason = self.budgets.check(profile["provider_id"], self.usage.estimate(request.task))
            if not budget_ok:
                continue
            candidates.append((provider, f"{capability_reason}; {reason}", budget_reason))
        if request.preferred_provider:
            candidates.sort(key=lambda item: item[0].profile.provider_id != request.preferred_provider)
        elif request.role == BrainRole.MASTER:
            candidates.sort(key=lambda item: item[0].profile.provider_id != self.master_provider)
        if not candidates:
            return {"status": "unavailable", "reason": "no available provider satisfies the request", "candidates": self.registry.list()}
        provider, match_reason, budget_reason = candidates[0]
        decision = {"status": "planned" if dry_run else "selected", "provider": provider.profile.provider_id,
                    "model": provider.profile.model_id, "reason": f"{match_reason}; {budget_reason}",
                    "candidates": [item[0].profile.provider_id for item in candidates]}
        if dry_run:
            return decision
        context = self.context.build(request)
        request.context_packet = context
        started = time.monotonic()
        response = provider.generate(request)
        response.duration = time.monotonic() - started
        response.metadata.setdefault("routing", decision)
        self.usage.record(response, request.task_type)
        self.budgets.record(provider.profile.provider_id, self.usage.estimate(request.task) + self.usage.estimate(response.content))
        return response.as_dict()