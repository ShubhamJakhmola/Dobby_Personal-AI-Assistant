import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from development.agent_detector import AgentDetector
from development.agent_registry import CodingAgentRegistry
from development.build.failure_classifier import FailureCategory, FailureClassifier
from development.build.implementation import ImplementationRunner, MockCodingAgent
from development.build.inspector import WorkspaceInspector
from development.build.models import BuildResult, BuildState, BuildTask
from development.build.planner import BuildPlanner
from development.build.repair import RepairPlanner
from development.build.state import BuildStateMachine, BuildStateStore
from development.build.verifier import BuildVerifier
from development.build.workflow import BuildWorkflow
from development.build_runner import BuildRunner
from development.models import CodingAgentInfo, CodingAgentState
from development.test_runner import TestRunner
from development.workspace import WorkspaceManager


class NoAgents:
    def available(self):
        return []


class OneAgent:
    def available(self):
        return [CodingAgentInfo("mock_real", "Mock Real", "test", "Mock", status=CodingAgentState.AVAILABLE,
                                installed=True, configured=True, available=True).as_dict()]


class PhaseTenTests(unittest.TestCase):
    def temp_workflow(self, mode="success"):
        temp = tempfile.TemporaryDirectory()
        manager = WorkspaceManager(temp.name)
        workflow = BuildWorkflow(manager, NoAgents(), ImplementationRunner(MockCodingAgent(mode)))
        return temp, manager, workflow

    def test_build_task_and_result_validation(self):
        self.assertFalse(BuildTask("", "p", "x").validate()[0])
        task = BuildTask("t", "p", "Create a script", timeout=1)
        self.assertTrue(task.validate()[0])
        result = BuildResult(BuildState.COMPLETED, "p", "t")
        self.assertTrue(result.validate()[0])

    def test_state_transitions_and_invalid_transitions(self):
        machine = BuildStateMachine()
        self.assertTrue(machine.transition(BuildState.SPECIFYING)[0])
        self.assertFalse(machine.transition(BuildState.TESTING)[0])

    def test_spec_plan_acceptance_persistence_and_secret_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspaceManager(directory).create_project("demo")
            task = BuildTask("t", workspace.project_id, "Build service password=secret-value",
                             acceptance_criteria=["main.py file exists"])
            planner = BuildPlanner(workspace.path)
            planner.write_spec(task); planner.write_plan(task); planner.write_acceptance(task)
            spec = (workspace.path / ".dobby" / "SPEC.md").read_text(encoding="utf-8")
            self.assertNotIn("secret-value", spec)
            self.assertTrue((workspace.path / ".dobby" / "PLAN.md").exists())
            self.assertTrue((workspace.path / ".dobby" / "ACCEPTANCE.md").exists())

    def test_available_agent_selection_and_no_agent_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            workflow = BuildWorkflow(WorkspaceManager(directory), OneAgent())
            self.assertEqual(workflow._select_agent()["id"], "mock_real")
            blocked = BuildWorkflow(WorkspaceManager(directory), NoAgents()).run("demo", "Build something")
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertIn("No compatible coding agent", blocked["final_summary"])

    def test_mock_success_end_to_end(self):
        temp, _, workflow = self.temp_workflow("success")
        try:
            result = workflow.run("demo", "Create a Python script that prints Hello Dobby")
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["build_status"], "PASS")
            self.assertEqual(result["test_status"], "PASS")
            self.assertIn("SPEC", result["phases_completed"])
        finally:
            temp.cleanup()

    def test_build_failure_then_repair(self):
        temp, _, workflow = self.temp_workflow("repair_success")
        try:
            result = workflow.run("demo", "Create a Python script that prints Hello Dobby")
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["repair_cycles"], 1)
            self.assertEqual(result["build_status"], "PASS")
        finally:
            temp.cleanup()

    def test_repair_limit_no_fourth_attempt(self):
        temp, manager, workflow = self.temp_workflow("build_failure")
        try:
            workspace = manager.create_project("demo")
            task = BuildTask("t", workspace.project_id, "Create invalid until limit", max_repair_cycles=3, timeout=5)
            result = workflow.run("demo", task=task)
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual(result["repair_cycles"], 3)
        finally:
            temp.cleanup()

    def test_workspace_escape_blocks_workflow(self):
        temp, _, workflow = self.temp_workflow("workspace_escape")
        try:
            result = workflow.run("demo", "Attempt workspace escape")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["verification_status"], "WORKSPACE_VIOLATION")
        finally:
            temp.cleanup()

    def test_test_failure_then_repair(self):
        temp, _, workflow = self.temp_workflow("test_failure")
        try:
            result = workflow.run("demo", "Create script with tests")
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["repair_cycles"], 1)
            self.assertEqual(result["test_status"], "PASS")
        finally:
            temp.cleanup()

    def test_mock_timeout_and_malformed_result(self):
        temp, _, workflow = self.temp_workflow("timeout")
        try:
            result = workflow.run("demo", "Timeout")
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(result["failures"])
        finally:
            temp.cleanup()
        temp, _, workflow = self.temp_workflow("malformed_result")
        try:
            result = workflow.run("demo", "Malformed")
            self.assertIn(result["status"], {"FAILED", "COMPLETED_UNVERIFIED"})
        finally:
            temp.cleanup()

    def test_workspace_inspection_unexpected_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspaceManager(directory).create_project("demo")
            before = WorkspaceInspector(workspace.path).snapshot()
            (workspace.path / "unexpected.txt").write_text("x", encoding="utf-8")
            result = WorkspaceInspector(workspace.path).inspect(before, ["src"])
            self.assertIn("unexpected.txt", result.created_files)
            self.assertIn("unexpected.txt", result.unexpected_files)

    def test_build_and_test_success_failure_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(directory)
            workspace = manager.create_project("demo")
            (workspace.path / "ok.py").write_text("x = 1\n", encoding="utf-8")
            self.assertTrue(BuildRunner(manager).run(workspace.path, [sys.executable, "-m", "compileall", "-q", "."], 5)["success"])
            self.assertFalse(BuildRunner(manager).run(workspace.path, [sys.executable, "-c", "import sys; sys.exit(2)"], 5)["success"])
            self.assertTrue(TestRunner(manager).run(workspace.path, [sys.executable, "-c", "assert True"], 5)["success"])
            self.assertFalse(TestRunner(manager).run(workspace.path, [sys.executable, "-c", "assert False"], 5)["success"])
            timeout = TestRunner(manager).run(workspace.path, [sys.executable, "-c", "import time; time.sleep(5)"], 0.2)
            self.assertEqual(timeout["status"], "timed_out")

    def test_failure_classification(self):
        classifier = FailureClassifier()
        self.assertEqual(classifier.classify({"phase": "build", "stderr": "SyntaxError"})["category"], FailureCategory.BUILD_ERROR)
        self.assertEqual(classifier.classify({"phase": "test", "stderr": "assert 1 == 2"})["category"], FailureCategory.TEST_FAILURE)
        self.assertEqual(classifier.classify({"timed_out": True})["category"], FailureCategory.TIMEOUT)
        self.assertEqual(classifier.classify({"workspace_violation": True})["category"], FailureCategory.WORKSPACE_VIOLATION)

    def test_repair_task_generation_and_context_bounding(self):
        task = BuildTask("t", "p", "Objective", max_repair_cycles=2)
        repair = RepairPlanner().create(task, {"category": "BUILD_ERROR", "summary": "x" * 5000}, ["a.py"], ["one", "two", "three"])
        self.assertLessEqual(len(repair.error_summary), 2000)
        self.assertEqual(repair.previous_attempts, ["two", "three"])

    def test_final_verification_completed_unverified(self):
        verifier = BuildVerifier()
        result = verifier.verify(agent_result={"status": "completed_unverified"},
                                 inspection={"changed_files": ["main.py"], "created_files": ["main.py"]},
                                 build_result={"success": True}, test_result=None, acceptance_criteria=[])
        self.assertEqual(result["state"], BuildState.COMPLETED_UNVERIFIED)

    def test_cancellation_persistence_resume_and_history(self):
        temp, manager, workflow = self.temp_workflow("success")
        try:
            workflow.run("demo", "Create script")
            cancelled = workflow.cancel("demo")
            self.assertEqual(cancelled["status"], "CANCELLED")
            resumed = workflow.resume("demo")
            self.assertTrue(resumed["success"])
            self.assertEqual(resumed["status"], "CANCELLED")
            self.assertTrue(workflow.history("demo")["success"])
        finally:
            temp.cleanup()

    def test_dry_run_has_no_source_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(directory)
            workflow = BuildWorkflow(manager, NoAgents())
            result = workflow.run("demo", "Build dry", dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertFalse((Path(directory) / "demo").exists())

    def test_build_state_store(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspaceManager(directory).create_project("demo")
            task = BuildTask("t", workspace.project_id, "Objective")
            result = BuildResult(BuildState.BLOCKED, workspace.project_id, "t")
            store = BuildStateStore(workspace.path)
            store.save(task, BuildState.BLOCKED, result)
            self.assertEqual(store.load()["state"], "BLOCKED")

    def test_diagnostics_and_cli(self):
        status = subprocess.run([sys.executable, "-m", "dobby", "build", "status"],
                                capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(status.returncode, 0)
        self.assertTrue(json.loads(status.stdout)["enabled"])
        dry = subprocess.run([sys.executable, "-m", "dobby", "build", "run", "demo", "Build dry", "--dry-run"],
                             capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(dry.returncode, 0)
        self.assertTrue(json.loads(dry.stdout)["dry_run"])

    def test_agent_factory_supervisor_paths_exist(self):
        from agents.factory import AgentFactory
        from agents.registry import AgentRegistry
        from agents.supervisor import AgentSupervisor

        factory = AgentFactory(Mock(names=lambda: {"filesystem_read"}), Mock(), AgentRegistry())
        self.assertTrue(hasattr(factory, "create_coding_spec"))
        self.assertTrue(hasattr(AgentSupervisor(Mock(), AgentRegistry()), "run_coding_agent"))


if __name__ == "__main__":
    unittest.main()
