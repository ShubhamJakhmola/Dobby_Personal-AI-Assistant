import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.execution import run_command
from core.action_loader import discover_actions
from security.audit import recent
from security.policy import L1, L3, classify


class PhaseOneTests(unittest.TestCase):
    def test_terminal_captures_real_result(self):
        result = run_command([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"])
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.stdout.strip(), "out")
        self.assertEqual(result.stderr.strip(), "err")

    def test_policy_blocks_privileged_commands(self):
        self.assertEqual(classify("terminal_execute", {"command": ["sudo", "id"]}).level, L3)
        self.assertTrue(classify("terminal_execute", {"command": ["printf", "ok"]}).allowed)
        self.assertEqual(classify("terminal_execute", {"command": ["printf", "ok"]}).level, L1)

    def test_audit_redacts_secret_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DOBBY_DATA_DIR": directory}):
            from security.audit import record
            record(selected_tool="test", password="secret-value", result=True)
            entry = recent(1)[0]
            self.assertNotIn("secret-value", json.dumps(entry))
            self.assertEqual(entry["password"], "[REDACTED]")

    def test_new_actions_are_discoverable(self):
        registry = discover_actions(Path(__file__).parents[1] / "actions", logger=lambda _: None)
        self.assertTrue({"terminal_execute", "process_manager", "application_manager", "task_scheduler"}.issubset(registry.names()))


if __name__ == "__main__":
    unittest.main()