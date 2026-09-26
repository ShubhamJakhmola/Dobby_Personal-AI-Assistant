"""Phase 19 Test Suite — Autonomous General-Purpose Agent (35 Test Cases).

All test cases use deterministic mocks or temporary local paths.
No external network, email, messaging, or phone connections are made.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from autonomous.action_contract import ActionRequest, ActionResult, ActionStatus
from autonomous.authorization import Authorization, AuthorizationStore
from autonomous.capability_router import CapabilityCategory, CapabilityRouter
from autonomous.context_builder import ContextBuilder
from autonomous.executor import AutonomousExecutor
from autonomous.goal import Goal, GoalStatus
from autonomous.goal_manager import GoalManager
from autonomous.idempotency import IdempotencyStore
from autonomous.planner import AutonomousPlanner
from autonomous.recovery import FailureCategory, RecoveryEngine, RecoveryStrategy
from autonomous.risk import RiskLevel, categorize_action
from autonomous.task_graph import GoalTask, TaskGraph
from autonomous.timeline import TaskTimeline, TimelineEvent, recent_for_goal
from capabilities.base import CapabilityProvider, CapabilityStatus
from capabilities.browser import BrowserCapabilityProvider
from capabilities.email import EmailCapabilityProvider
from capabilities.messaging import MessagingCapabilityProvider
from capabilities.phone import PhoneCapabilityProvider
from capabilities.registry import CapabilityRegistry
from capabilities.web_research import WebResearchCapability
from computer.diagnostics import collect_environment, format_report


class DummyProvider(CapabilityProvider):

    def __init__(self, name: str, category: str = "builtin", status: CapabilityStatus = CapabilityStatus.AVAILABLE):
        self._name = name
        self._category = category
        self._status = status

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    def status(self) -> CapabilityStatus:
        return self._status

    def execute(self, request: ActionRequest) -> ActionResult:
        return ActionResult(
            action_id=request.action_id,
            status=ActionStatus.SUCCESS,
            output={"result": "ok", "provider": self._name},
        )


class TestPhase19AutonomousAgent(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.tmp_path = Path(self.temp_dir.name)

    # 1. Goal creation
    def test_01_goal_creation(self):
        g = Goal(original_request="Find test data", normalized_objective="Find test data")
        self.assertEqual(g.status, GoalStatus.CREATED)
        self.assertTrue(g.goal_id.startswith("goal-"))
        d = g.as_dict()
        self.assertEqual(d["original_request"], "Find test data")

    # 2. Normalization
    def test_02_normalization(self):
        mgr = GoalManager(storage_path=self.tmp_path / "goals.json")
        g = mgr.create_goal("  dobby, please find the latest logs  ")
        self.assertEqual(g.normalized_objective, "Find the latest logs")

    # 3. Plan generation
    def test_03_plan_generation(self):
        planner = AutonomousPlanner(brain_router=None)
        g = Goal(original_request="search Python docs", normalized_objective="Search Python docs")
        graph = planner.plan(g, dry_run=True)
        self.assertGreater(len(graph), 0)
        self.assertTrue(graph.is_valid())

    # 4. Task graph
    def test_04_task_graph(self):
        graph = TaskGraph(goal_id="g1")
        t1 = GoalTask(task_id="t1", parent_goal="g1", capability="web_research")
        t2 = GoalTask(task_id="t2", parent_goal="g1", capability="web_research", dependencies=["t1"])
        graph.add_task(t1)
        graph.add_task(t2)
        self.assertTrue(graph.is_valid())
        order = graph.topological_sort()
        self.assertEqual([t.task_id for t in order], ["t1", "t2"])

    # 5. Dependency handling / Cycle detection
    def test_05_dependency_handling_cycle(self):
        graph = TaskGraph(goal_id="g1")
        t1 = GoalTask(task_id="t1", parent_goal="g1", dependencies=["t2"])
        t2 = GoalTask(task_id="t2", parent_goal="g1", dependencies=["t1"])
        graph.add_task(t1)
        graph.add_task(t2)
        self.assertFalse(graph.is_valid())

    # 6. Capability selection
    def test_06_capability_selection(self):
        router = CapabilityRouter()
        p = DummyProvider("web_research", category="web")
        router.register(p)
        task = GoalTask(task_id="t1", parent_goal="g1", capability="web_research")
        selected = router.route(task)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "web_research")

    # 7. Provider selection with risk gates
    def test_07_provider_selection_risk(self):
        router = CapabilityRouter()
        p = DummyProvider("email.send", category="email")
        router.register(p)
        task = GoalTask(task_id="t1", parent_goal="g1", capability="email.send", risk_level=RiskLevel.IRREVERSIBLE_EXTERNAL.value)
        req = router.build_request(task)
        self.assertEqual(req.risk_level, RiskLevel.IRREVERSIBLE_EXTERNAL)

    # 8. Autonomous step execution
    def test_08_autonomous_step_execution(self):
        router = CapabilityRouter()
        p = DummyProvider("test_cap")
        router.register(p)

        executor = AutonomousExecutor(capability_router=router)
        g = Goal(original_request="test execution")
        graph = TaskGraph(goal_id=g.goal_id)
        t = GoalTask(task_id="t1", parent_goal=g.goal_id, capability="test_cap")
        graph.add_task(t)

        res = executor.execute(g, graph)
        self.assertTrue(res["success"])
        self.assertIn("t1", res["completed_tasks"])

    # 9. Verification
    def test_09_verification(self):
        router = CapabilityRouter()
        router.register(DummyProvider("verified_cap"))
        executor = AutonomousExecutor(capability_router=router)

        g = Goal(original_request="verified execution")
        graph = TaskGraph(goal_id=g.goal_id)
        t = GoalTask(task_id="t1", parent_goal=g.goal_id, capability="verified_cap",
                     verification={"type": "contains", "key": "result", "expected": "ok"})
        graph.add_task(t)

        res = executor.execute(g, graph)
        self.assertTrue(res["success"])

    # 10. Retry
    def test_10_retry(self):
        calls = 0

        class FlakyProvider(CapabilityProvider):
            @property
            def name(self) -> str: return "flaky"
            def status(self) -> CapabilityStatus: return CapabilityStatus.AVAILABLE
            def execute(self, request: ActionRequest) -> ActionResult:
                nonlocal calls
                calls += 1
                if calls == 1:
                    return ActionResult(action_id=request.action_id, status=ActionStatus.FAILED, error="transient network error")
                return ActionResult(action_id=request.action_id, status=ActionStatus.SUCCESS, output={"ok": True})

        router = CapabilityRouter()
        router.register(FlakyProvider())
        executor = AutonomousExecutor(capability_router=router, recovery_engine=RecoveryEngine(router))

        g = Goal(original_request="flaky execution")
        graph = TaskGraph(goal_id=g.goal_id)
        t = GoalTask(task_id="t1", parent_goal=g.goal_id, capability="flaky")
        graph.add_task(t)

        res = executor.execute(g, graph)
        self.assertTrue(res["success"])
        self.assertEqual(calls, 2)

    # 11. Recovery classification
    def test_11_recovery_classification(self):
        engine = RecoveryEngine()
        strat = engine.classify_and_select("t1", "Connection timed out after 30s")
        self.assertEqual(strat.category, FailureCategory.TRANSIENT)
        self.assertEqual(strat.strategy, RecoveryStrategy.RETRY)

    # 12. Replanning requirement on unrecoverable failure
    def test_12_replanning_on_failure(self):
        class BrokenProvider(CapabilityProvider):
            @property
            def name(self) -> str: return "broken"
            def status(self) -> CapabilityStatus: return CapabilityStatus.AVAILABLE
            def execute(self, request: ActionRequest) -> ActionResult:
                return ActionResult(action_id=request.action_id, status=ActionStatus.FAILED, error="Permanent failure")

        router = CapabilityRouter()
        router.register(BrokenProvider())
        rec = RecoveryEngine(router)
        executor = AutonomousExecutor(capability_router=router, recovery_engine=rec)

        g = Goal(original_request="broken test")
        graph = TaskGraph(goal_id=g.goal_id)
        graph.add_task(GoalTask(task_id="t1", parent_goal=g.goal_id, capability="broken", retry_policy={"max_retries": 1}))

        res = executor.execute(g, graph)
        self.assertTrue(res.get("replan_required", False))

    # 13. Task persistence
    def test_13_task_persistence(self):
        storage = self.tmp_path / "goals.json"
        mgr1 = GoalManager(storage_path=storage)
        g1 = mgr1.create_goal("Persist this goal")
        mgr2 = GoalManager(storage_path=storage)
        g2 = mgr2.inspect_goal(g1.goal_id)
        self.assertEqual(g2["normalized_objective"], "Persist this goal")

    # 14. Goal pause and resume
    def test_14_pause_resume(self):
        mgr = GoalManager(storage_path=self.tmp_path / "goals.json")
        g = mgr.create_goal("Pause and resume me")
        g.transition(GoalStatus.EXECUTING)
        p_res = mgr.pause_goal(g.goal_id)
        self.assertTrue(p_res["success"])
        self.assertEqual(g.status, GoalStatus.WAITING)

    # 15. Idempotency store
    def test_15_idempotency_store(self):
        store = IdempotencyStore(storage_path=self.tmp_path / "idem.json")
        self.assertFalse(store.check("key1"))
        res = ActionResult(action_id="act1", status=ActionStatus.SUCCESS, output={"sent": True})
        store.record("key1", "email.send", {"to": "a@b.com"}, res)
        self.assertTrue(store.check("key1"))

    # 16. Duplicate action protection in executor
    def test_16_duplicate_action_protection(self):
        router = CapabilityRouter()
        p = DummyProvider("idem_cap")
        router.register(p)
        idem = IdempotencyStore(storage_path=self.tmp_path / "idem.json")
        executor = AutonomousExecutor(capability_router=router, idempotency_store=idem)

        # Pre-record idempotency key
        idem.record("k1", "idem_cap", {}, ActionResult(action_id="prev", status=ActionStatus.SUCCESS, output={"cached": True}))

        g = Goal(original_request="idem test")
        graph = TaskGraph(goal_id=g.goal_id)
        graph.add_task(GoalTask(task_id="t1", parent_goal=g.goal_id, capability="idem_cap", parameters={"_idempotency_key": "k1"}))

        res = executor.execute(g, graph)
        self.assertTrue(res["success"])

    # 17. Confirmation-required state
    def test_17_confirmation_required(self):
        class HighRiskProvider(CapabilityProvider):
            @property
            def name(self) -> str: return "high_risk"
            def status(self) -> CapabilityStatus: return CapabilityStatus.REQUIRES_CONFIRMATION
            def execute(self, request: ActionRequest) -> ActionResult:
                return ActionResult(action_id=request.action_id, status=ActionStatus.SUCCESS)

        router = CapabilityRouter()
        router.register(HighRiskProvider())
        executor = AutonomousExecutor(capability_router=router)

        g = Goal(original_request="high risk task")
        graph = TaskGraph(goal_id=g.goal_id)
        graph.add_task(GoalTask(task_id="t1", parent_goal=g.goal_id, capability="high_risk", risk_level=RiskLevel.IRREVERSIBLE_EXTERNAL.value))

        res = executor.execute(g, graph)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], GoalStatus.WAITING.value)

    # 18. Scoped authorization
    def test_18_scoped_authorization(self):
        auth_store = AuthorizationStore(storage_path=self.tmp_path / "auth.json")
        auth_store.grant("email.send", {"recipient_domain": "example.com"})
        auth = auth_store.check("email.send", {"recipient": "user@example.com"})
        self.assertIsNotNone(auth)

    # 19. Authorization revocation
    def test_19_authorization_revocation(self):
        auth_store = AuthorizationStore(storage_path=self.tmp_path / "auth.json")
        grant = auth_store.grant("email.send")
        self.assertTrue(auth_store.revoke(grant.auth_id))
        auth = auth_store.check("email.send")
        self.assertIsNone(auth)

    # 20. Worker creation routing
    def test_20_worker_creation(self):
        router = CapabilityRouter()
        p = DummyProvider("worker_spawn", category="coding_agent")
        router.register(p)
        task = GoalTask(task_id="t1", parent_goal="g1", capability="worker_spawn")
        selected = router.route(task)
        self.assertEqual(selected.category, "coding_agent")

    # 21. Worker result verification
    def test_21_worker_result_verification(self):
        router = CapabilityRouter()
        router.register(DummyProvider("worker_task"))
        executor = AutonomousExecutor(capability_router=router)
        g = Goal(original_request="worker test")
        graph = TaskGraph(goal_id=g.goal_id)
        graph.add_task(GoalTask(task_id="t1", parent_goal=g.goal_id, capability="worker_task",
                                verification={"type": "non_empty", "key": "result"}))
        res = executor.execute(g, graph)
        self.assertTrue(res["success"])

    # 22. Coding-agent routing
    def test_22_coding_agent_routing(self):
        router = CapabilityRouter()
        task = GoalTask(task_id="t1", parent_goal="g1", capability="coding_agent")
        req = router.build_request(task)
        self.assertEqual(req.capability, "coding_agent")

    # 23. MCP routing
    def test_23_mcp_routing(self):
        router = CapabilityRouter()
        task = GoalTask(task_id="t1", parent_goal="g1", capability="mcp.github")
        req = router.build_request(task)
        self.assertEqual(req.capability, "mcp.github")

    # 24. Browser capability provider
    def test_24_browser_capability(self):
        bp = BrowserCapabilityProvider()
        self.assertIn(bp.status(), [CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE, CapabilityStatus.NOT_CONFIGURED])
        req = ActionRequest(action_id="a1", goal_id="g1", task_id="t1", capability="browser", parameters={"action": "navigate", "url": "https://example.com"})
        res = bp.execute(req)
        self.assertIn(res.status, [ActionStatus.SUCCESS, ActionStatus.NOT_SUPPORTED, ActionStatus.FAILED])

    # 25. Email capability provider abstraction
    def test_25_email_capability(self):
        ep = EmailCapabilityProvider()
        self.assertEqual(ep.status(), CapabilityStatus.NOT_CONFIGURED)
        req = ActionRequest(action_id="a1", goal_id="g1", task_id="t1", capability="email.send")
        res = ep.execute(req)
        self.assertEqual(res.status, ActionStatus.NOT_CONFIGURED)

    # 26. Messaging capability provider abstraction
    def test_26_messaging_capability(self):
        mp = MessagingCapabilityProvider()
        self.assertEqual(mp.status(), CapabilityStatus.NOT_CONFIGURED)
        req = ActionRequest(action_id="a1", goal_id="g1", task_id="t1", capability="messaging.send")
        res = mp.execute(req)
        self.assertEqual(res.status, ActionStatus.NOT_CONFIGURED)

    # 27. Phone capability provider abstraction
    def test_27_phone_capability(self):
        pp = PhoneCapabilityProvider()
        self.assertEqual(pp.status(), CapabilityStatus.NOT_CONFIGURED)
        req = ActionRequest(action_id="a1", goal_id="g1", task_id="t1", capability="call.start")
        res = pp.execute(req)
        self.assertEqual(res.status, ActionStatus.NOT_CONFIGURED)

    # 28. Failure classification
    def test_28_failure_classification(self):
        engine = RecoveryEngine()
        strat = engine.classify_and_select("t1", "401 Unauthorized access denied")
        self.assertEqual(strat.category, FailureCategory.AUTHENTICATION)

    # 29. Dry-run execution mode
    def test_29_dry_run_mode(self):
        router = CapabilityRouter()
        p = DummyProvider("dry_cap")
        router.register(p)
        executor = AutonomousExecutor(capability_router=router)

        g = Goal(original_request="dry run goal", dry_run=True)
        graph = TaskGraph(goal_id=g.goal_id)
        graph.add_task(GoalTask(task_id="t1", parent_goal=g.goal_id, capability="dry_cap"))

        res = executor.execute(g, graph, dry_run=True)
        self.assertTrue(res["success"])
        self.assertTrue(res.get("dry_run"))

    # 30. Audit logging
    def test_30_audit_logging(self):
        with patch("security.audit.record") as mock_record:
            mgr = GoalManager(storage_path=self.tmp_path / "goals.json")
            g = mgr.create_goal("Audit this goal")
            mock_record.assert_called()

    # 31. Secret rejection
    def test_31_secret_rejection(self):
        cat = categorize_action("email.send", {"api_key": "sk-1234567890"})
        self.assertEqual(cat, RiskLevel.SENSITIVE)

    # 32. Bounded context builder
    def test_32_bounded_context_builder(self):
        cb = ContextBuilder()
        g = Goal(original_request="context test")
        pkt = cb.build_context(g, current_step="Step 1", recent_results=[{"t1": "ok"}])
        self.assertEqual(pkt.task, "context test")
        self.assertEqual(len(pkt.messages), 1)

    # 33. Diagnostics integration
    def test_33_diagnostics_integration(self):
        env = collect_environment()
        self.assertIn("autonomous", env)
        report = format_report(env)
        self.assertIn("Autonomous Engine (Phase 19):", report)

    # 34. CLI goal status / list
    def test_34_cli_goal_commands(self):
        from dobby.__main__ import main
        with patch("sys.argv", ["dobby", "goal", "status"]):
            with patch("sys.stdout"):
                ret = main()
                self.assertEqual(ret, 0)

    # 35. Regression test — existing system compatibility
    def test_35_regression_existing_systems(self):
        registry = CapabilityRegistry()
        all_caps = registry.list_capabilities()
        self.assertGreater(len(all_caps), 0)


if __name__ == "__main__":
    unittest.main()
