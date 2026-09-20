import tempfile
import unittest
from pathlib import Path

from agents.factory import AgentFactory
from agents.models import AgentState, AgentSpec
from agents.persistence import AgentPersistence
from agents.registry import AgentRegistry
from agents.supervisor import AgentSupervisor
from brain.models import BrainProfile, BrainRole, ProviderHealth
from brain.registry import BrainRegistry
from brain.response import BrainResponse
from brain.router import BrainRouter


class FakeProvider:
    def __init__(self, capabilities=None):
        self.profile = BrainProfile("local", "worker-model", BrainRole.SPECIALIST,
                                    capabilities or ["reasoning", "classification"],
                                    "medium", 8000, True, "local", True, True)

    def health_check(self):
        return ProviderHealth(True, "available")

    def generate(self, request):
        return BrainResponse("local", "worker-model", "completed", "analysis result",
                             usage={"usage_available": False}, metadata={"request_text": request.task})


class FakeActions:
    def names(self):
        return {"filesystem_read", "process_manager"}


class PhaseSevenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = BrainRegistry()
        self.registry.register(FakeProvider())
        self.brain_router = BrainRouter(self.registry)
        self.agents = AgentRegistry(AgentPersistence(Path(self.temp.name)))
        self.factory = AgentFactory(FakeActions(), self.brain_router, self.agents)

    def tearDown(self):
        self.temp.cleanup()

    def test_simple_task_does_not_need_agent(self):
        needed, reason = self.factory.should_create("create test.txt", task_type="file_create")
        self.assertFalse(needed)
        self.assertIn("direct", reason)

    def test_complex_task_needs_agent(self):
        needed, _ = self.factory.should_create("investigate recurring crash", task_type="investigation",
                                              complexity="high", required_capabilities=["filesystem.read", "process.manager"])
        self.assertTrue(needed)

    def test_factory_rejects_unavailable_capability(self):
        result = self.factory.create_spec("Analyze logs", capabilities=["web.search"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error_category"], "capability_unavailable")

    def test_factory_assigns_brain_through_router(self):
        result = self.factory.create_spec("Analyze logs", name="log_analysis_agent",
                                          capabilities=["filesystem.read"],
                                          brain_requirements={"capabilities": ["reasoning"], "privacy": "local"})
        self.assertTrue(result["success"])
        self.assertEqual(result["spec"]["brain"]["provider"], "local")
        self.assertEqual(result["spec"]["agent_type"], "temporary")

    def test_temporary_agent_is_not_persisted_after_destroy(self):
        result = self.factory.create_spec("Analyze logs", capabilities=["filesystem.read"])
        agent_id = result["spec"]["agent_id"]
        self.assertIsNotNone(self.agents.get(agent_id))
        self.assertTrue(self.agents.destroy(agent_id))
        self.assertIsNone(self.agents.get(agent_id))

    def test_persistent_agent_requires_explicit_opt_in(self):
        result = self.factory.create_spec("Review repository", agent_type="persistent", persistent=True,
                                          capabilities=["filesystem.read"])
        self.assertTrue(result["success"])
        self.assertTrue((Path(self.temp.name) / "agents.json").exists())
        self.assertTrue(result["spec"]["persistent"])

    def test_supervisor_returns_worker_result_unverified(self):
        result = self.factory.create_spec("Analyze logs", capabilities=["filesystem.read"])
        supervisor = AgentSupervisor(self.brain_router, self.agents)
        worker = supervisor.run(result["spec"]["agent_id"], "Analyze the log evidence")
        self.assertTrue(worker["success"])
        self.assertEqual(worker["status"], AgentState.COMPLETED)
        self.assertFalse(worker["verification"]["verified"])

    def test_supervisor_missing_agent_fails_structured(self):
        worker = AgentSupervisor(self.brain_router, self.agents).run("missing", "work")
        self.assertFalse(worker["success"])
        self.assertEqual(worker["status"], AgentState.FAILED)

    def test_worker_does_not_receive_os_executor(self):
        result = self.factory.create_spec("Analyze logs", capabilities=["filesystem.read"])
        self.assertNotIn("executor", result["spec"])
        self.assertNotIn("confirmation", result["spec"])


if __name__ == "__main__":
    unittest.main()