"""Universal computer-use execution engine.

This is the platform-neutral boundary between Dobby's reasoning layer and the
actual machine.  It deliberately does not contain an LLM: the model proposes
an action, this engine applies policy, executes it, observes the machine and
records the result.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable

from computer.state import get_state, observe_desktop, update_state
from memory.experience import record as record_experience


class ComputerEngine:
    """Execute bounded computer actions with observation and verification."""

    def __init__(self, registry, policy: Callable[[str, dict], Any] | None = None,
                 confirmer: Callable[[str, dict, str], bool] | None = None):
        self.registry = registry
        self.policy = policy
        self.confirmer = confirmer

    @staticmethod
    def _decode(raw: Any) -> tuple[bool, dict[str, Any]]:
        if isinstance(raw, dict):
            return bool(raw.get("success", True)), raw
        text = str(raw or "")
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "success" in obj:
                return bool(obj["success"]), obj
        except Exception:
            pass
        lowered = text.lower()
        failed = any(token in lowered for token in (
            "failed", "error:", "error_category", "could not", "not found",
            "timed out", "unsupported", "unknown action",
        ))
        return not failed, {"result": raw}

    def execute(self, action: str, parameters: dict[str, Any] | None = None,
                *, goal: str = "", verify: bool = True, retries: int = 1) -> dict[str, Any]:
        params = dict(parameters or {})
        before = observe_desktop()

        if self.policy is not None:
            decision = self.policy(action, params)
            allowed = getattr(decision, "allowed", True)
            requires = getattr(decision, "requires_confirmation", False)
            reason = getattr(decision, "reason", "")
            if not allowed and not requires:
                return {"success": False, "status": "policy_denied", "action": action,
                        "error": reason, "verified": False, "before": before}
            if requires:
                if self.confirmer is None or not self.confirmer(action, params, reason):
                    return {"success": False, "status": "waiting_confirmation", "action": action,
                            "error": reason, "verified": False, "before": before}

        attempts = 0
        last = None
        while attempts <= max(0, retries):
            attempts += 1
            raw = self.registry.run(action, params, {})
            success, decoded = self._decode(raw)
            last = decoded
            after = observe_desktop()
            update_state(last_action={
                "action": action, "parameters": params, "success": success,
                "attempt": attempts, "timestamp": time.time(),
            }, last_observation=after)

            verified = success
            verification: dict[str, Any] = {"before": before, "after": after}
            # Tool-level verification may be stronger than the generic desktop
            # observation.  A JSON tool result declaring success is accepted as
            # the tool's own verification; desktop actions also get a state diff.
            if isinstance(decoded, dict) and decoded.get("verified") is not None:
                verified = bool(decoded.get("verified"))
                verification["tool"] = decoded.get("verification")

            record_experience(goal or get_state().task_goal or "computer task",
                             action, success, decoded, recovery=attempts > 1)
            if success and (not verify or verified):
                return {"success": True, "status": "completed", "action": action,
                        "attempts": attempts, "result": decoded, "verified": verified,
                        "verification": verification, "computer_state": get_state().snapshot()}

            if attempts <= max(0, retries):
                # Refresh state before a bounded retry. Never repeat indefinitely.
                before = after
                time.sleep(0.15)

        return {"success": False, "status": "failed", "action": action,
                "attempts": attempts, "result": last, "verified": False,
                "computer_state": get_state().snapshot()}
