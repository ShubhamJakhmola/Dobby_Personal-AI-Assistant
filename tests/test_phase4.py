import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.runtime import AgentRuntime
from browser.manager import BrowserManager
from computer.linux import screen
from computer.models import Monitor
from core.action_loader import discover_actions
from security.policy import L1, L3, classify
from vision.capture import capture_status


def registry():
    return discover_actions(Path(__file__).parents[1] / "actions", logger=lambda _: None)


class FakeMss:
    monitors = [{"left": 0, "top": 0, "width": 300, "height": 200},
                {"left": 20, "top": 10, "width": 100, "height": 80}]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class PhaseFourTests(unittest.TestCase):
    def test_computer_actions_are_registered(self):
        names = registry().names()
        self.assertTrue({"computer_screen", "computer_input", "computer_clipboard",
                         "computer_window", "computer_application"}.issubset(names))

    def test_gemini_style_action_enters_local_runtime(self):
        runtime = AgentRuntime(registry())
        result = runtime.execute_registered("computer_screen", {"operation": "list_monitors"})
        self.assertIn(result["status"], {"completed", "completed_unverified"})
        self.assertEqual(result["action"], "computer_screen")

    def test_normal_computer_action_is_autonomous(self):
        decision = classify("computer_input", {"operation": "click", "x": 1, "y": 1})
        self.assertEqual(decision.level, L1)
        self.assertFalse(decision.requires_confirmation)

    def test_sensitive_keyboard_content_is_gated(self):
        decision = classify("computer_input", {"operation": "type", "text": "password=secret"})
        self.assertEqual(decision.level, L3)
        self.assertTrue(decision.requires_confirmation)

    def test_monitor_enumeration_is_dynamic(self):
        with patch.object(screen, "mss", FakeMss), patch.object(screen.platform, "system", return_value="Linux"):
            monitors = screen.list_monitors()
        self.assertEqual(len(monitors), 1)
        self.assertEqual(monitors[0].width, 100)
        self.assertTrue(monitors[0].primary)

    def test_invalid_monitor_is_structured(self):
        with patch.object(screen, "mss", FakeMss), patch.object(screen.platform, "system", return_value="Linux"):
            result = screen.capture_monitor(99)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "monitor_not_found")

    def test_invalid_frame_is_structured(self):
        result = screen._diagnose(b"", 0, 0, "test", 0)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "invalid_frame")

    def test_black_frame_detection(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow unavailable")
        image = Image.new("RGB", (10, 10), (0, 0, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        result = screen._diagnose(buffer.getvalue(), 10, 10, "test", 0)
        self.assertTrue(result.success)
        self.assertTrue(result.black_frame)
        self.assertEqual(result.error_category, "black_frame_detected")

    def test_browser_unavailable_is_explicit(self):
        status = BrowserManager().status()
        self.assertIn("available", status)
        if status["available"] is False:
            self.assertEqual(status["error_category"], "browser_automation_unavailable")

    def test_vision_status_is_structured(self):
        status = capture_status()
        self.assertIn("available", status)
        self.assertIn("backends", status)

    def test_action_metadata_reports_computer_risk(self):
        metadata = registry().metadata("computer_input")
        self.assertEqual(metadata["risk_level"], "L1")
        self.assertTrue(metadata["supports_verification"])


if __name__ == "__main__":
    unittest.main()