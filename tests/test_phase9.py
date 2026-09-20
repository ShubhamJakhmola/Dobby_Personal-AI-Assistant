import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from development.adapters.base import BaseCliAdapter
from development.adapters.generic_cli import GenericCliAdapter
from development.agent_detector import AgentDetector
from development.agent_registry import CodingAgentRegistry
from development.agent_supervisor import CodingAgentSupervisor
from development.build_runner import BuildRunner
from development.models import CodingAgentState, CodingTask
from development.project_manager import ProjectManager
from development.redaction import redact_text
from development.test_runner import TestRunner
from development.verification import verify_agent_result
from development.workspace import WorkspaceBoundary, WorkspaceManager


class PythonAdapter(BaseCliAdapter):
    id = "python_mock"
    name = "Python Mock"
    provider = "local"
    executable_names = (sys.executable,)
    version_args = ("--version",)
    supports_workspace = True
    supports_headless = True
    supports_noninteractive = True

    def _invocation_supported(self, executable):
        return True


class MissingAdapter(BaseCliAdapter):
    id = "missing_mock"
    name = "Missing Mock"
    provider = "local"
    executable_names = ("definitely-not-a-dobby-agent",)


class PhaseNineTests(unittest.TestCase):
    def test_agent_model_validation(self):
        self.assertFalse(CodingTask("", "do it").validate()[0])
        self.assertFalse(CodingTask("p1", "").validate()[0])
        self.assertTrue(CodingTask("p1", "do it", timeout=1).validate()[0])

    def test_detection_when_executable_exists_and_version_parses(self):
        info = PythonAdapter().detect()
        self.assertTrue(info.installed)
        self.assertEqual(info.status, CodingAgentState.AVAILABLE)
        self.assertIn("Python", info.version)

    def test_detection_when_executable_does_not_exist(self):
        info = MissingAdapter().detect()
        self.assertFalse(info.installed)
        self.assertEqual(info.status, CodingAgentState.NOT_FOUND)

    def test_configuration_and_unavailable_state(self):
        class InstalledUnsupported(PythonAdapter):
            id = "unsupported"

            def _invocation_supported(self, executable):
                return False

        info = InstalledUnsupported().detect()
        self.assertTrue(info.installed)
        self.assertFalse(info.available)
        self.assertEqual(info.status, CodingAgentState.UNAVAILABLE)

    def test_generic_cli_stdout_stderr_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            result = GenericCliAdapter(sys.executable).run_command(
                [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
                Path(directory),
                timeout=5,
            )
        self.assertTrue(result.success)
        self.assertIn("out", result.stdout)
        self.assertIn("err", result.stderr)

    def test_timeout_and_process_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            result = GenericCliAdapter(sys.executable).run_command(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                Path(directory),
                timeout=0.2,
            )
        self.assertTrue(result.timed_out)
        self.assertEqual(result.status, "timed_out")

    def test_output_truncation_and_secret_redaction(self):
        self.assertNotIn("secret-value", redact_text("password=secret-value"))
        with tempfile.TemporaryDirectory() as directory:
            result = GenericCliAdapter(sys.executable, output_limit=20).run_command(
                [sys.executable, "-c", "print('x'*100); print('api_key=secret-value')"],
                Path(directory),
                timeout=5,
            )
        self.assertTrue(result.truncated)
        self.assertNotIn("secret-value", result.stdout)

    def test_workspace_creation_boundary_state_and_log(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = WorkspaceManager(directory)
            workspace = manager.create_project("My Project")
            self.assertTrue((workspace.path / ".dobby" / "SPEC.md").exists())
            self.assertTrue(manager.validate_workspace(workspace.path)[0])
            self.assertFalse(manager.validate_workspace(Path(directory).parent)[0])
            manager.update_state(workspace.path, status="active", last_task="test")
            state = manager.read_state(workspace.path)
            self.assertEqual(state.status, "active")
            manager.append_event(workspace.path, "task_sent", {"token": "secret-value"})
            log = (workspace.path / ".dobby" / "AGENT_LOG.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("secret-value", log)
            self.assertTrue(WorkspaceBoundary(workspace.path).contains(workspace.path / "file.txt"))
            self.assertFalse(WorkspaceBoundary(workspace.path).contains(Path(directory).parent))

    def test_project_manager_and_state_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ProjectManager(directory)
            created = manager.create_project("demo")
            located = manager.locate_project("demo")
            self.assertEqual(created["project_id"], located["project_id"])
            self.assertTrue(manager.validate_project(created["path"])["valid"])

    def test_agent_lifecycle_supervisor_and_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            wm = WorkspaceManager(directory)
            workspace = wm.create_project("demo")
            task = CodingTask(workspace.project_id, "hello", timeout=5)
            result = CodingAgentSupervisor(wm).run_generic(
                sys.executable,
                workspace.path,
                task,
                ["-c", "import sys; print('done:' + sys.argv[-1])"],
            )
            self.assertEqual(result["status"], "completed_unverified")
            verified = verify_agent_result(workspace.path, result, ["prints done"], wm)
            self.assertFalse(verified["verified"])

    def test_build_and_test_runner_failed_build_handling(self):
        with tempfile.TemporaryDirectory() as directory:
            wm = WorkspaceManager(directory)
            workspace = wm.create_project("demo")
            build = BuildRunner(wm).run(workspace.path, [sys.executable, "-c", "import sys; sys.exit(2)"], timeout=5)
            tests = TestRunner(wm).run(workspace.path, [sys.executable, "-c", "print('ok')"], timeout=5)
            self.assertFalse(build["success"])
            self.assertTrue(tests["success"])

    def test_bounded_repair_task_and_registry_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspaceManager(directory).create_project("demo")
            task = CodingTask(workspace.project_id, "fix bug", previous_failures=["a", "b", "c"])
            repair = CodingAgentSupervisor(max_retries=2).create_repair_task(task, "d")
            self.assertEqual(len(repair.previous_failures), 2)
        registry = CodingAgentRegistry(AgentDetector([PythonAdapter, MissingAdapter]))
        caps = registry.capabilities()
        self.assertEqual(caps[0]["name"], "coding_agent.python_mock")

    def test_cli_behavior(self):
        result = subprocess.run([sys.executable, "-m", "dobby", "coding", "detect"],
                                capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn("agents", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
