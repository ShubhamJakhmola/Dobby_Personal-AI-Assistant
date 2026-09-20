"""The local bridge from intent proposals to policy-checked verified actions."""
from __future__ import annotations

import json

from agent.capabilities import CapabilitySelector
from agent.intent import IntentParser
from security.policy import classify
from agent.legacy import adapt_legacy_result


class AgentRuntime:
    def __init__(self, registry, parser=None, selector=None):
        self.registry = registry
        self.parser = parser or IntentParser()
        self.selector = selector or CapabilitySelector()

    def list_capabilities(self) -> list[dict]:
        return self.selector.list_capabilities(self.registry)

    def execute_request(self, request: str, *, dry_run: bool = False, confirmation=None) -> dict:
        intent = self.parser.parse(request)
        action = self.selector.select(intent, self.registry)
        if not action:
            return self._failure(intent, "unknown_action", "No registered capability matches this request.")
        valid, message = self.registry.validate_parameters(action, intent.parameters)
        if not valid:
            return self._failure(intent, "invalid_arguments", message, action)
        decision = classify(action, intent.parameters)
        metadata = self.registry.metadata(action)
        if dry_run:
            return {"success": False, "status": "planned", "dry_run": True, "intent": intent.as_dict(),
                    "action": action, "risk_level": decision.level, "requires_confirmation": decision.requires_confirmation or metadata.get("requires_confirmation", False)}
        requires_confirmation = decision.requires_confirmation or metadata.get("requires_confirmation", False)
        if requires_confirmation:
            approved = bool(confirmation and confirmation(action, intent.parameters, decision.reason))
            if not approved:
                return self._failure(intent, "user_cancelled", "Confirmation was not approved.", action, status="waiting_confirmation")
        if not decision.allowed and not requires_confirmation:
            return self._failure(intent, "policy_denied", decision.reason, action)
        raw = self.registry.run(action, intent.parameters)
        result = self._decode(raw)
        verified = self._verify(intent, result)
        result.update({"intent": intent.as_dict(), "action": action, "verified": verified})
        if not verified:
            result["success"] = False
            result["status"] = "verification_failed"
            result["error_category"] = "verification_failed"
            result["error"] = result.get("error") or "The requested outcome could not be verified."
        return result

    def execute_registered(self, action: str, arguments: dict | None = None,
                           *, context: dict | None = None, confirmation=None) -> dict:
        """Execute a discovered action through validation and local policy.

        This is the bridge used by non-text callers such as Gemini function
        calls. The provider supplies only an action name and arguments; it
        cannot supply a confirmation token or bypass the policy decision.
        """
        arguments = arguments or {}
        valid, message = self.registry.validate_parameters(action, arguments)
        if not valid:
            return {"success": False, "status": "failed", "error_category": "invalid_arguments",
                    "error": message, "action": action, "verified": False}
        decision = classify(action, arguments)
        if decision.requires_confirmation:
            approved = bool(confirmation and confirmation(action, arguments, decision.reason))
            if not approved:
                return {"success": False, "status": "waiting_confirmation", "error_category": "user_cancelled",
                        "error": "Confirmation was not approved.", "action": action, "verified": False}
        if not decision.allowed and not decision.requires_confirmation:
            return {"success": False, "status": "failed", "error_category": "policy_denied",
                    "error": decision.reason, "action": action, "verified": False}
        raw = self.registry.run(action, arguments, context)
        result = self._decode(raw)
        result["action"] = action
        result.setdefault("verified", bool(result.get("verified", False)))
        if result.get("success") and not result["verified"]:
            result["success"] = False
            result["status"] = "completed_unverified"
        return result

    def _verify(self, intent, result: dict) -> bool:
        expected = intent.expected_outcome
        if not expected:
            return False
        if expected.get("exit_code") is not None:
            return result.get("exit_code") == expected["exit_code"]
        if expected.get("file_exists"):
            return bool(result.get("verified") or result.get("file_exists"))
        if expected.get("process_running"):
            return bool(result.get("running") or result.get("process_running"))
        if expected.get("schedule_exists"):
            return bool(result.get("verified") or result.get("success"))
        return bool(result.get("verified"))

    @staticmethod
    def _decode(raw) -> dict:
        return adapt_legacy_result(raw)

    @staticmethod
    def _failure(intent, category, error, action="", status="failed") -> dict:
        return {"success": False, "status": status, "error_category": category, "error": error,
                "action": action, "intent": intent.as_dict(), "verified": False}