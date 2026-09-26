from __future__ import annotations

import time

from brain.models import BrainProfile, BrainRole, ProviderHealth
from brain.response import BrainResponse
from providers.gemini import GeminiProvider


class GeminiBrainProvider:
    def __init__(self, delegate=None):
        self.delegate = delegate or GeminiProvider()
        self.profile = BrainProfile("gemini", "configured-gemini", BrainRole.MASTER,
                                   ["reasoning", "planning", "classification", "search", "vision", "structured_output"],
                                   "high", 12000, True, "external_api", True, True)

    def health_check(self):
        from core.gemini import api_key
        available = bool(api_key())
        return ProviderHealth(available, "available" if available else "unconfigured",
                              "Gemini API key configured" if available else "Gemini API key missing")

    def generate(self, request):
        if not self.health_check().available:
            return BrainResponse("gemini", self.profile.model_id, "unavailable", errors=["Gemini API key missing"])
        prompt = request.task + "\n\nContext:\n" + str(request.context_packet or {})
        try:
            content = self.delegate.text(prompt, timeout_ms=10000)
            return BrainResponse("gemini", self.profile.model_id, "completed", content=content,
                                 usage={"usage_available": False}, metadata={"request_text": prompt})
        except TimeoutError as exc:
            return BrainResponse("gemini", self.profile.model_id, "timeout", errors=[str(exc)])
        except Exception as exc:
            return BrainResponse("gemini", self.profile.model_id, "failed", errors=[str(exc)])