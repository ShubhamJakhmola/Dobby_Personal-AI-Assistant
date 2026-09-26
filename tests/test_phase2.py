import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.planner import PlanStep, Planner
from agent.task_manager import TaskManager, TaskState
from agent.verification.filesystem import verify_file_exists
from agent.workflow import Workflow
from core.execution import run_command
from scheduler.cron import CronScheduler


class PhaseTwoTests(unittest.TestCase):
    def test_failed_command_is_structured(self):
        result = run_command([sys.executable, "-c", "raise SystemExit(4)"])
        self.assertFalse(result.success)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_category, "command_failed")

    def test_timeout_is_structured(self):
        result = run_command([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.05)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "timeout")
        self.assertEqual(result.error_category, "timeout")

    def test_verification_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "tasks.json"
            plan = Planner().from_steps("missing file", [PlanStep("write", lambda _: "executed")])
            result = Workflow(tasks=TaskManager(store)).run("verify-fail", plan)
        self.assertFalse(result["success"])
        self.assertEqual(result["results"][0]["status"], "verification_failed")

    def test_recovery_retries_and_verifies(self):
        attempts = {"count": 0}

        def action(_):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary failure")
            return "ready"

        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "tasks.json"
            plan = Planner().from_steps("recover", [PlanStep("start", action, expected=lambda value: value == "ready", retries=1)])
            result = Workflow(tasks=TaskManager(store)).run("recover", plan)
        self.assertTrue(result["success"])
        self.assertEqual(attempts["count"], 2)

    def test_task_state_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.json"
            manager = TaskManager(path)
            task = manager.create("abc", "persist me")
            task.state = TaskState.PAUSED
            manager._save()
            restored = TaskManager(path)
            self.assertEqual(restored.tasks["abc"].goal, "persist me")
            self.assertEqual(restored.tasks["abc"].state, TaskState.PAUSED)

    def test_filesystem_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.txt"
            path.write_text("expected", encoding="utf-8")
            self.assertTrue(verify_file_exists(str(path), "expected").verified)
            self.assertFalse(verify_file_exists(str(path), "wrong").verified)

    def test_cron_verification_checks_command(self):
        scheduler = CronScheduler()
        scheduler._read = lambda: ["0 2 * * * /usr/bin/python /tmp/backup.py # dobby-task:backup"]
        with patch("scheduler.cron.platform.system", return_value="Linux"), patch("scheduler.cron.shutil.which", return_value="crontab"):
            self.assertTrue(scheduler.verify("backup", "0 2 * * *", ["/usr/bin/python", "/tmp/backup.py"]))
            self.assertFalse(scheduler.verify("backup", "0 3 * * *", ["/usr/bin/python", "/tmp/backup.py"]))

    def test_privileged_terminal_routes_to_local_confirmation(self):
        from actions.terminal import terminal_execute
        with patch("core.confirm.request", return_value="pending") as request:
            self.assertEqual(terminal_execute({"command": ["sudo", "id"]}), "pending")
            request.assert_called_once()


if __name__ == "__main__":
    unittest.main()