import tempfile
import unittest
from pathlib import Path

from brain.budgets import BudgetManager
from brain.defaults import create_registry
from brain.models import BrainProfile, BrainRole, ProviderHealth
from brain.request import BrainRequest
from brain.response import BrainResponse
from brain.registry import BrainRegistry
from brain.router import BrainRouter
from brain.usage import UsageTracker
from memory.packet import ContextPacket


class FakeProvider:
    def __init__(self, provider_id="local", available=True, capabilities=None, privacy="local"):
        self.profile = BrainProfile(provider_id, "fake-model", BrainRole.SPECIALIST,
                                    capabilities or ["classification"],  "medium", 10000, True, privacy, True, available)
        self.calls = 0

    def health_check(self):
        return ProviderHealth(self.profile.available, "available" if self.profile.available else "unavailable")

    def generate(self, request):
        self.calls += 1
        return BrainResponse(self.profile.provider_id, self.profile.model_id, "completed", "worker result",
                             usage={"usage_available": False}, metadata={"request_text": request.task})


class PhaseSixTests(unittest.TestCase):
    def test_registry_registration_lookup_and_availability(self):
        registry = BrainRegistry()
        provider = FakeProvider()
        registry.register(provider)
        self.assertIs(registry.get("local"), provider)
        self.assertEqual(len(registry.list_available()), 1)
        registry.unregister("local")
        self.assertEqual(registry.list_available(), [])

    def test_gemini_is_explicit_master(self):
        profiles = create_registry().list()
        gemini = next(item for item in profiles if item["provider_id"] == "gemini")
        self.assertEqual(gemini["role"], "master")

    def test_specialist_capability_routing_and_explanation(self):
        registry = BrainRegistry()
        local = FakeProvider(capabilities=["classification"])
        registry.register(local)
        decision = BrainRouter(registry).route(BrainRequest("classify logs", task_type="classification",
                                                            required_capabilities=["classification"], privacy_level="local"), dry_run=True)
        self.assertEqual(decision["provider"], "local")
        self.assertIn("capabilities", decision["reason"])

    def test_unavailable_provider_is_not_selected(self):
        registry = BrainRegistry()
        registry.register(FakeProvider(available=False))
        result = BrainRouter(registry).route(BrainRequest("classify", required_capabilities=["classification"], privacy_level="local"), dry_run=True)
        self.assertEqual(result["status"], "unavailable")

    def test_no_automatic_fallback_on_provider_failure(self):
        class Failing(FakeProvider):
            def generate(self, request):
                return BrainResponse("local", "fake-model", "failed", errors=["provider failed"])
        registry = BrainRegistry()
        failing = Failing()
        other = FakeProvider("other")
        registry.register(failing)
        registry.register(other)
        result = BrainRouter(registry).route(BrainRequest("classify", required_capabilities=["classification"], privacy_level="local"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(failing.calls, 0)
        self.assertEqual(other.calls, 0)

    def test_budget_is_internal_and_blocks_selection(self):
        registry = BrainRegistry()
        registry.register(FakeProvider())
        router = BrainRouter(registry, budgets=BudgetManager({"local": {"daily_request_limit": 0}}))
        result = router.route(BrainRequest("classify", required_capabilities=["classification"], privacy_level="local"), dry_run=True)
        self.assertEqual(result["status"], "unavailable")

    def test_usage_distinguishes_estimate_from_actual(self):
        tracker = UsageTracker()
        item = tracker.record(BrainResponse("local", "fake", "completed", "output", usage={"usage_available": False}, metadata={"request_text": "input"}))
        self.assertFalse(item["usage_available"])
        self.assertGreater(item["estimated_input_tokens"], 0)
        self.assertEqual(item["input_tokens"], 0)

    def test_context_packet_is_brokered_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            router = BrainRouter(BrainRegistry(), context_broker=__import__("brain.context", fromlist=["BrainContextBroker"]).BrainContextBroker(Path(directory)))
            request = BrainRequest("classify", max_context=200, context_requirements={"max_characters": 200})
            packet = router.context.build(request)
            self.assertLessEqual(len(str(packet)), 500)
            self.assertIn("current_context", packet)
            self.assertIn("relevant_memory", packet)
            self.assertIsNone(packet["task"])

    def test_external_provider_rejected_for_local_privacy(self):
        registry = BrainRegistry()
        registry.register(FakeProvider("cloud", privacy="external_api"))
        result = BrainRouter(registry).route(BrainRequest("classify", required_capabilities=["classification"], privacy_level="local"), dry_run=True)
        self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()