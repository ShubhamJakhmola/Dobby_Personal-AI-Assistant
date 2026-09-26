import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from computer.state import get_state, reset_state, update_state
from agent.control_runtime import ControlRuntime
from core.action_loader import ActionRegistry, ActionRecord

class ComputerRuntimeTests(unittest.TestCase):
    def tearDown(self):
        reset_state()

    def test_state_roundtrip(self):
        update_state(active_application="Chrome", active_url="https://youtube.com/watch?v=x", media_state="playing")
        state=get_state().snapshot()
        self.assertEqual(state["active_application"],"Chrome")
        self.assertEqual(state["media_state"],"playing")

    def test_runtime_updates_state_and_records_success(self):
        def handler(parameters=None, **kwargs): return "Clicked the current button"
        rec=ActionRecord(name="computer_control",description="test",parameters={"type":"OBJECT","properties":{}},handler=handler,valid=True)
        reg=ActionRegistry({"computer_control":rec}, logger=lambda _:None)
        rt=ControlRuntime(reg)
        out=rt.execute("computer_control", {"action":"click"})
        self.assertTrue(out["success"])
        self.assertTrue(out["verified"])
        self.assertEqual(get_state().last_action["action"],"computer_control")

if __name__ == "__main__": unittest.main()
