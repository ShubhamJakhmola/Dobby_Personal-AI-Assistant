from __future__ import annotations

from brain.context import BrainContextBroker


class AgentContext:
    """Builds the worker's bounded context through the Phase 5/6 broker."""
    def __init__(self, broker=None):
        self.broker = broker or BrainContextBroker()

    def build(self, request, requirements: dict | None = None) -> dict:
        requirements = requirements or {}
        request.context_requirements = requirements
        return self.broker.build(request)