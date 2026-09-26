import json
from computer.os_adapters import get_os_adapter
from computer.state import reset_state, get_state
from core.master_orchestrator import DobbyOrchestrator
from agent.control_runtime import ControlRuntime


class FakeRegistry:
    def __init__(self, result): self.result = result
    def run(self, action, args, context): return self.result


def test_os_adapter_has_common_contract():
    a = get_os_adapter()
    assert a.name in {"windows", "macos", "linux"}
    assert "os" in a.environment()


def test_control_runtime_honours_json_failure():
    rt = ControlRuntime(FakeRegistry(json.dumps({"success": False, "error": "nope"})))
    reset_state()
    out = rt.execute("test_action", retries=0)
    assert out["success"] is False


def test_orchestrator_persists_task_context():
    reset_state()
    orch = DobbyOrchestrator(FakeRegistry(json.dumps({"success": True, "verified": True})))
    started = orch.start_task("test computer task")
    assert started["task_id"]
    assert get_state().task_goal == "test computer task"
    result = orch.act("test_action", retries=0)
    assert result["success"] is True
    assert result["computer_state"]["task_goal"] == "test computer task"
