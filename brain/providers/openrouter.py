from __future__ import annotations

import os
from brain.models import BrainProfile, BrainRole, ProviderHealth
from brain.response import BrainResponse


class OpenRouterBrainProvider:
    def __init__(self):
        configured = bool(os.environ.get("OPENROUTER_API_KEY"))
        self.profile = BrainProfile("openrouter", os.environ.get("DOBBY_OPENROUTER_MODEL", ""), BrainRole.SPECIALIST,
                                   ["classification", "summarization", "code_analysis"], "varied", 8000, True, "external_api", configured, False)

    def health_check(self):
        return ProviderHealth(False, "unavailable", "OpenRouter adapter is not enabled in this phase")

    def generate(self, request):
        return BrainResponse("openrouter", self.profile.model_id, "unavailable", errors=["OpenRouter adapter unavailable"])