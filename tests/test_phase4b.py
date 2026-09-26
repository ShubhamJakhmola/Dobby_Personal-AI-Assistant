import unittest
from unittest.mock import patch

from computer.diagnostics import collect_environment, format_report, run_live_validation


class PhaseFourBLiveValidationTests(unittest.TestCase):
    def test_current_non_linux_host_is_not_claimed_live_verified(self):
        with patch("computer.diagnostics.environment", return_value={"os": "Windows", "kernel": "test", "python": "test", "desktop": "unknown", "display_server": "unknown"}):
            result = run_live_validation()
        self.assertEqual(result["status"], "unavailable_on_current_host")
        self.assertEqual(result["input"]["status"], "not_run")

    def test_diagnostics_report_contains_backend_sections(self):
        with patch("computer.diagnostics.environment", return_value={"os": "Linux", "kernel": "test", "python": "test", "desktop": "GNOME", "display_server": "Wayland", "monitors": []}):
            with patch("computer.diagnostics.screen.detect_backends", return_value=[]):
                data = collect_environment()
        report = format_report(data)
        self.assertIn("Dobby Linux Diagnostics", report)
        self.assertIn("Screen Capture:", report)
        self.assertIn("Window Manager:", report)

    def test_live_validation_does_not_store_frames(self):
        result = run_live_validation()
        self.assertNotIn("frame", result)


if __name__ == "__main__":
    unittest.main()