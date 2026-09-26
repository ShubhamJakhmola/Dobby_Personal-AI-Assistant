from __future__ import annotations

import os
from brain.models import BrainProfile, BrainRole, ProviderHealth
from brain.response import BrainResponse


class GroqBrainProvider:
    def __init__(self):
        configured = bool(os.environ.get("GROQ_API_KEY"))
        self.profile = BrainProfile("groq", os.environ.get("DOBBY_GROQ_MODEL", ""), BrainRole.SPECIALIST,
                                   ["classification", "summarization"], "high", 8000, True, "external_api", configured, False)

    def health_check(self):
        return ProviderHealth(False, "unavailable", "Groq adapter is not enabled in this phase")

    def generate(self, request):
        return BrainResponse("groq", self.profile.model_id, "unavailable", errors=["Groq adapter unavailable"])