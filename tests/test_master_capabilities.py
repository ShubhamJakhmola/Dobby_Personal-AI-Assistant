import json
import tempfile
import unittest
from pathlib import Path

from actions.media_control import media_control
from actions.system_intelligence import system_intelligence
from actions.troubleshoot import troubleshoot
from actions.dobby_self import dobby_self


class MasterCapabilitiesTests(unittest.TestCase):
    def test_local_media_missing_file_is_safe(self):
        result = json.loads(media_control({"operation": "play", "path": "/definitely/not/a/real/movie.mp4"}))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_category"], "file_not_found")

    def test_system_specs_are_read_only(self):
        result = json.loads(system_intelligence({"operation": "specs"}))
        self.assertIn("system", result)
        self.assertIn("ram_total_gb", result)

    def test_cleanup_is_analysis_only(self):
        result = json.loads(system_intelligence({"operation": "cleanup_candidates", "min_ram_mb": 999999}))
        self.assertIn("candidates", result)
        self.assertEqual(result["candidates"], [])
        self.assertIn("warning", result)

    def test_troubleshoot_plan_is_non_destructive(self):
        result = json.loads(troubleshoot({"operation": "plan_fix", "target": "system"}))
        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "plan_only")

    def test_self_model_explicitly_distinguishes_consciousness(self):
        result = json.loads(dobby_self({"operation": "status"}))
        self.assertFalse(result["consciousness"]["literal"])
        self.assertIn("persistent self-model", result["consciousness"]["implemented"])


if __name__ == "__main__":
    unittest.main()
