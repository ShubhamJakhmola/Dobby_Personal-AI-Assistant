from __future__ import annotations

from brain.providers import GeminiBrainProvider, GroqBrainProvider, OllamaBrainProvider, OpenRouterBrainProvider
from brain.registry import BrainRegistry


def create_registry() -> BrainRegistry:
    registry = BrainRegistry()
    registry.register(GeminiBrainProvider())
    registry.register(OllamaBrainProvider())
    registry.register(GroqBrainProvider())
    registry.register(OpenRouterBrainProvider())
    return registry