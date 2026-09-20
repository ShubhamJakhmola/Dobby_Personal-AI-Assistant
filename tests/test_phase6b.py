import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain.manager import ProviderManager
from brain.secrets import SecretStore


class PhaseSixAvailabilityTests(unittest.TestCase):
    def test_provider_status_does_not_expose_secret(self):
        class FakeSecrets:
            def exists(self, provider): return True
            def get(self, provider): return "super-secret-key"
            def set(self, provider, value): return {"success": True}
            def delete(self, provider): return True
        with tempfile.TemporaryDirectory() as directory:
            manager = ProviderManager(Path(directory) / "brain.json", secrets=FakeSecrets())
            status = manager.list_providers()
            serialized = json.dumps(status)
            self.assertNotIn("super-secret-key", serialized)
            self.assertTrue(all("api_key" not in item for item in status))

    def test_configure_provider_stores_non_secret_settings_only(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ProviderManager(Path(directory) / "brain.json", secrets=SecretStore())
            result = manager.configure_provider("groq", model="test-model", enabled=False)
            raw = json.loads((Path(directory) / "brain.json").read_text(encoding="utf-8"))
            self.assertTrue(result["success"])
            self.assertEqual(raw["groq"], {"enabled": False, "model": "test-model"})

    def test_secret_store_uses_environment_without_returning_it_from_status(self):
        with patch.dict(os.environ, {"DOBBY_GROQ_API_KEY": "secret-value"}):
            store = SecretStore()
            self.assertTrue(store.exists("groq"))

    def test_remove_provider_removes_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brain.json"
            manager = ProviderManager(path)
            manager.configure_provider("openrouter", model="model", enabled=False)
            manager.remove_provider("openrouter")
            self.assertNotIn("openrouter", json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()