from __future__ import annotations

from typing import Any

from security.policy import classify


class ControlledMCPProvider:
    """A safe external capability adapter that never bypasses Dobby policy."""

    def __init__(self, name: str, capabilities: dict[str, dict[str, Any]] | None = None):
        self.name = name
        self._capabilities = capabilities or {}
        self.enabled = True
        self.revoked = False
        self.disabled = False
        self.status = "AVAILABLE"

    def supports(self, capability: str) -> bool:
        return capability in self._capabilities

    def capabilities(self) -> list[str]:
        return sorted(self._capabilities.keys())

    def policy_gate(self, capability: str, parameters: dict[str, Any], decision: Any | None = None) -> bool:
        if not self.enabled or self.revoked or getattr(self, "disabled", False):
            return False
        if capability == "terminal.execute":
            effective = decision or classify("terminal_execute", parameters)
            return bool(effective.allowed and not effective.requires_confirmation)
        if capability in {"process.list", "process.status", "filesystem.list", "filesystem.stat"}:
            return True
        return True

    def request(self, capability: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if not self.supports(capability):
            return {"status": "UNSUPPORTED", "provider": self.name, "capability": capability}
        if not self.enabled or self.revoked or getattr(self, "disabled", False):
            return {"status": "BLOCKED", "provider": self.name, "capability": capability, "reason": "provider disabled or revoked"}
        decision = classify("terminal_execute", parameters) if capability == "terminal.execute" else None
        if capability == "terminal.execute" and not self.policy_gate(capability, parameters, decision):
            return {"status": "BLOCKED", "provider": self.name, "capability": capability, "reason": "L3 or policy gate rejected execution"}
        return {"status": "READY", "provider": self.name, "capability": capability, "parameters": parameters}


class MCPRegistry:
    def __init__(self):
        self._providers: dict[str, ControlledMCPProvider] = {}

    def register(self, provider: ControlledMCPProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, provider_name: str) -> ControlledMCPProvider | None:
        return self._providers.get(provider_name)

    def request(self, capability: str, parameters: dict[str, Any]) -> dict[str, Any]:
        for provider in self._providers.values():
            if provider.supports(capability):
                return {"provider": provider.name, "capability": capability, "status": "REQUESTED", "parameters": parameters}
        return {"provider": "none", "capability": capability, "status": "UNAVAILABLE"}

    def execute(self, capability: str, parameters: dict[str, Any]) -> dict[str, Any]:
        for provider in self._providers.values():
            if not provider.supports(capability):
                continue
            if not provider.enabled or provider.revoked or getattr(provider, "disabled", False):
                return {"status": "BLOCKED", "provider": provider.name, "capability": capability, "reason": "provider disabled or revoked"}
            req = provider.request(capability, parameters)
            if req["status"] == "READY":
                return {"status": "READY", "provider": provider.name, "capability": capability, "result": req["parameters"]}
            return {"status": "BLOCKED", "provider": provider.name, "capability": capability, "reason": req.get("reason", "blocked")}
        return {"status": "BLOCKED", "provider": "none", "capability": capability, "reason": "unsupported capability"}
