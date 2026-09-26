from __future__ import annotations

from brain.models import ProviderHealth


class BrainRegistry:
    def __init__(self):
        self._providers = {}

    def register(self, provider) -> None:
        self._providers[provider.profile.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str):
        return self._providers.get(provider_id)

    def list(self) -> list[dict]:
        profiles = []
        for provider in self._providers.values():
            profile = provider.profile.as_dict()
            health = provider.health_check()
            profile["available"] = health.available
            profile["availability_status"] = health.status
            profile["availability_reason"] = health.reason
            profiles.append(profile)
        return profiles

    def health(self, provider_id: str) -> ProviderHealth:
        provider = self.get(provider_id)
        return ProviderHealth(False, "unavailable", "provider is not registered") if provider is None else provider.health_check()

    def list_available(self) -> list[dict]:
        return [profile for profile in self.list() if self.health(profile["provider_id"]).available]