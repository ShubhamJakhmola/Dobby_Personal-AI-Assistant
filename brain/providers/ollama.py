from __future__ import annotations

import os

import requests

from brain.models import BrainProfile, BrainRole, ProviderHealth
from brain.response import BrainResponse


class OllamaBrainProvider:
    def __init__(self, model=""):
        selected_model = model or os.environ.get("DOBBY_OLLAMA_MODEL", "")
        self.profile = BrainProfile(
            "ollama", selected_model, BrainRole.SPECIALIST,
            ["classification", "summarization", "code_analysis"],
            "medium", 8000, True, "local", bool(selected_model), False,
            "configure DOBBY_OLLAMA_MODEL",
        )
        self.endpoint = os.environ.get("DOBBY_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.models: list[str] = []

    def health_check(self):
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=1)
            if response.status_code != 200:
                return ProviderHealth(False, "error", f"Ollama returned HTTP {response.status_code}")
            data = response.json()
            self.models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
            self.profile.available = bool(self.models)
            self.profile.configured = True
            return ProviderHealth(bool(self.models), "available" if self.models else "unavailable",
                                  f"{len(self.models)} model(s) detected")
        except Exception:
            return ProviderHealth(False, "unavailable", "Ollama is not reachable")

    def generate(self, request):
        return BrainResponse("ollama", self.profile.model_id, "unavailable",
                             errors=["Ollama is not available"])
