from __future__ import annotations

from typing import Protocol

from brain.models import BrainProfile, ProviderHealth
from brain.request import BrainRequest
from brain.response import BrainResponse


class BrainProvider(Protocol):
    profile: BrainProfile

    def health_check(self) -> ProviderHealth:
        ...

    def generate(self, request: BrainRequest) -> BrainResponse:
        ...