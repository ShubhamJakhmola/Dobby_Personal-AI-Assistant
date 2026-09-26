from __future__ import annotations

import json
import os
import time
from pathlib import Path

from brain.defaults import create_registry
from brain.secrets import SecretStore


class ProviderManager:
    """Safe provider configuration/status facade. Secrets never leave SecretStore."""
    def __init__(self, config_path: str | Path | None = None, registry=None, secrets=None):
        self.config_path = Path(config_path or Path.home() / ".dobby" / "brain.json")
        self.registry = registry or create_registry()
        self.secrets = secrets or SecretStore()

    def _config(self) -> dict:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            self.config_path.chmod(0o600)
        except OSError:
            pass

    def list_providers(self) -> list[dict]:
        return [self._safe_status(profile) for profile in self.registry.list()]

    def _safe_status(self, profile: dict) -> dict:
        provider_id = profile["provider_id"]
        config = self._config().get(provider_id, {})
        enabled = bool(config.get("enabled", True))
        credential = provider_id == "ollama" or self.secrets.exists(provider_id)
        status = "disabled" if not enabled else profile.get("availability_status", "unavailable")
        if enabled and profile.get("available") and credential:
            status = "available"
        elif enabled and not credential and provider_id not in {"ollama"}:
            status = "not_configured"
        return {"provider": provider_id, "model": config.get("model") or profile.get("model_id", ""),
                "role": profile.get("role"), "enabled": enabled, "configured": credential,
                "credential_configured": credential, "available": status == "available",
                "status": status, "privacy": profile.get("privacy"),
                "capabilities": profile.get("capabilities", []),
                "availability_reason": profile.get("availability_reason", "")}

    def configure_provider(self, provider: str, *, model: str = "", enabled: bool = True, api_key: str = "") -> dict:
        data = self._config()
        data[provider] = {"enabled": bool(enabled), "model": model}
        if api_key:
            secret_result = self.secrets.set(provider, api_key)
            if not secret_result.get("success"):
                return {"success": False, "provider": provider, "error": "secure secret storage unavailable", "details": secret_result}
        self._save(data)
        return {"success": True, **next(item for item in self.list_providers() if item["provider"] == provider)}

    def enable_provider(self, provider: str) -> dict:
        return self.configure_provider(provider, enabled=True)

    def disable_provider(self, provider: str) -> dict:
        return self.configure_provider(provider, enabled=False)

    def remove_provider(self, provider: str) -> dict:
        data = self._config()
        data.pop(provider, None)
        self._save(data)
        self.secrets.delete(provider)
        return {"success": True, "provider": provider, "status": "not_configured"}

    def refresh(self) -> list[dict]:
        """Refresh provider metadata; adapters decide whether a health probe is safe."""
        return self.list_providers()

    def test_provider(self, provider: str) -> dict:
        target = self.registry.get(provider)
        if target is None:
            return {"success": False, "provider": provider, "status": "unavailable", "error": "unknown provider"}
        started = time.monotonic()
        health = target.health_check()
        return {"success": health.available, "provider": provider, "status": health.status,
                "reason": health.reason, "latency": round(time.monotonic() - started, 3)}

    def list_models(self, provider: str) -> list[str]:
        target = self.registry.get(provider)
        return list(getattr(target, "models", []) or [])