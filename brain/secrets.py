from __future__ import annotations

import os


class SecretStore:
    """Secret abstraction: environment first, optional OS keyring second.

    Plain provider keys are never written to brain configuration or memory.
    """
    def __init__(self, service: str = "dobby"):
        self.service = service

    def _env_name(self, provider: str) -> str:
        return f"DOBBY_{provider.upper()}_API_KEY"

    def set(self, provider: str, value: str) -> dict:
        try:
            import keyring
            keyring.set_password(self.service, provider, value)
            return {"success": True, "storage": "keyring"}
        except ImportError:
            return {"success": False, "storage": "environment", "error": f"set {self._env_name(provider)} in the environment"}
        except Exception as exc:
            return {"success": False, "storage": "keyring", "error": str(exc)}

    def get(self, provider: str) -> str:
        env = os.environ.get(self._env_name(provider), "")
        if env:
            return env
        if provider == "gemini":
            try:
                from core.gemini import api_key
                return api_key()
            except Exception:
                pass
        try:
            import keyring
            return keyring.get_password(self.service, provider) or ""
        except Exception:
            return ""

    def delete(self, provider: str) -> bool:
        try:
            import keyring
            keyring.delete_password(self.service, provider)
            return True
        except Exception:
            return False

    def exists(self, provider: str) -> bool:
        return bool(self.get(provider))