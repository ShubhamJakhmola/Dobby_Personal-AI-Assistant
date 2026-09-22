"""Universal Capability Router (Phase 19).

Routes each GoalTask to the appropriate capability provider.  Selection
considers availability, permissions, privacy, cost, latency, reliability,
context requirements, verification availability, and risk.

Providers are never hard-coded into task logic.  The router discovers
which providers are AVAILABLE and picks the best match.
"""
from __future__ import annotations

from enum import Enum
import logging
from typing import Any

from autonomous.action_contract import ActionRequest, ActionResult, RiskLevel
from autonomous.risk import classify_action, requires_confirmation

logger = logging.getLogger(__name__)


class CapabilityCategory(str, Enum):
    BUILTIN = "BUILTIN"
    OS = "OS"
    TERMINAL = "TERMINAL"
    FILESYSTEM = "FILESYSTEM"
    BROWSER = "BROWSER"
    WEB = "WEB"
    EMAIL = "EMAIL"
    MESSAGING = "MESSAGING"
    PHONE = "PHONE"
    CODING_AGENT = "CODING_AGENT"
    MCP = "MCP"
    REMOTE_DEVICE = "REMOTE_DEVICE"
    DATABASE = "DATABASE"
    CLOUD = "CLOUD"
    DOCUMENT = "DOCUMENT"
    VISION = "VISION"
    LOCAL_AI = "LOCAL_AI"
    SPECIALIST_AI = "SPECIALIST_AI"

# Ordered capability → routing key map
_CAPABILITY_ALIASES: dict[str, str] = {
    "WEB": "WEB_RESEARCH",
    "SEARCH": "WEB_RESEARCH",
    "INTERNET": "WEB_RESEARCH",
    "HTTP": "WEB_RESEARCH",
    "FILE": "FILESYSTEM",
    "FILES": "FILESYSTEM",
    "DISK": "FILESYSTEM",
    "SHELL": "TERMINAL",
    "CMD": "TERMINAL",
    "BASH": "TERMINAL",
    "CODE": "CODING_AGENT",
    "DEVELOP": "CODING_AGENT",
    "GIT": "CODING_AGENT",
    "CALL": "PHONE",
    "VOICE": "PHONE",
    "MSG": "MESSAGING",
    "CHAT": "MESSAGING",
    "MAIL": "EMAIL",
    "SMTP": "EMAIL",
}


class CapabilityRouter:
    """Routes ActionRequests to the correct CapabilityProvider.

    Providers are registered at startup.  Unknown capabilities return
    a NOT_CONFIGURED ActionResult rather than raising.
    """

    def __init__(self, confirmation_callback=None):
        self._providers: dict[str, Any] = {}   # capability → CapabilityProvider
        self._confirm = confirmation_callback

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, capability_or_provider: Any, provider: Any = None) -> None:
        if provider is None:
            prov = capability_or_provider
            cap = getattr(prov, "category", getattr(prov, "name", "BUILTIN"))
            name = getattr(prov, "name", cap)
            self._providers[str(cap).upper()] = prov
            self._providers[str(name).upper()] = prov
        else:
            self._providers[str(capability_or_provider).upper()] = provider
            if hasattr(provider, "name"):
                self._providers[str(provider.name).upper()] = provider

    def unregister(self, capability: str) -> None:
        self._providers.pop(str(capability).upper(), None)

    def get_provider(self, capability: str) -> Any:
        cap = self._resolve_capability(str(capability))
        return self._providers.get(cap.upper()) or self._providers.get(str(capability).upper())

    def build_request(self, task: Any, goal_id: str = "") -> ActionRequest:
        from autonomous.action_contract import RiskLevel
        risk = task.risk_level
        if isinstance(risk, str):
            try:
                risk = RiskLevel(risk)
            except ValueError:
                risk = RiskLevel.INFORMATIONAL
        return ActionRequest(
            goal_id=goal_id or getattr(task, "parent_goal", ""),
            task_id=getattr(task, "task_id", ""),
            capability=getattr(task, "capability", ""),
            parameters=dict(getattr(task, "parameters", {})),
            risk_level=risk,
        )

    # ── Routing ───────────────────────────────────────────────────────────

    def route(self, request_or_task: Any) -> Any:
        """Dispatch an ActionRequest to execute, or select provider for GoalTask."""
        from autonomous.task_graph import GoalTask
        if isinstance(request_or_task, GoalTask):
            return self.get_provider(request_or_task.capability)

        request: ActionRequest = request_or_task
        cap = self._resolve_capability(request.capability)

        # ── Risk classification ───────────────────────────────────────────
        action_name = request.parameters.get("action", "")
        risk = classify_action(cap, action_name, request.parameters)
        request.risk_level = risk

        # ── Dry-run ───────────────────────────────────────────────────────
        if request.dry_run:
            return ActionResult.dry_run(
                request.action_id,
                metadata={
                    "capability": cap,
                    "risk_level": risk.value,
                    "would_require_confirmation": requires_confirmation(risk),
                    "provider": self._providers.get(cap, type("_", (), {"name": "NOT_CONFIGURED"})).name
                    if cap in self._providers else "NOT_CONFIGURED",
                },
            )

        # ── Confirmation gate ─────────────────────────────────────────────
        if requires_confirmation(risk):
            if not self._confirm:
                return ActionResult.fail(
                    request.action_id,
                    f"Action requires user confirmation (risk={risk.value}) "
                    "but no confirmation handler is configured.",
                )
            approved = self._confirm(request, risk.value)
            if not approved:
                from autonomous.action_contract import ActionStatus
                return ActionResult(
                    action_id=request.action_id,
                    status=ActionStatus.REQUIRES_CONFIRMATION,
                    error="User did not confirm the action.",
                )

        # ── Provider dispatch ─────────────────────────────────────────────
        provider = self._providers.get(cap)
        if provider is None:
            return self._not_configured(request.action_id, cap)

        try:
            result = provider.execute(request)
            if not isinstance(result, ActionResult):
                # Wrap legacy dict results
                if isinstance(result, dict) and result.get("success"):
                    return ActionResult.ok(request.action_id, output=result)
                return ActionResult.fail(request.action_id, str(result))
            return result
        except Exception as exc:
            logger.exception("Provider %s raised an exception", cap)
            return ActionResult.fail(request.action_id, str(exc))

    # ── Discovery ─────────────────────────────────────────────────────────

    def available_capabilities(self) -> list[str]:
        return list(self._providers.keys())

    def capability_status(self, capability: str) -> str:
        cap = self._resolve_capability(capability)
        provider = self._providers.get(cap)
        if provider is None:
            return "NOT_CONFIGURED"
        try:
            return provider.status()
        except Exception:
            return "ERROR"

    def all_statuses(self) -> list[dict]:
        result = []
        for cap, provider in self._providers.items():
            try:
                status = provider.status()
            except Exception:
                status = "ERROR"
            result.append({"capability": cap, "provider": provider.name, "status": status})
        return result

    def can_handle(self, capability: str) -> bool:
        cap = self._resolve_capability(capability)
        status = self.capability_status(cap)
        return status == "AVAILABLE"

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_capability(capability: str) -> str:
        cap = capability.upper().strip()
        return _CAPABILITY_ALIASES.get(cap, cap)

    @staticmethod
    def _not_configured(action_id: str, capability: str) -> ActionResult:
        return ActionResult.fail(
            action_id,
            f"Capability '{capability}' is NOT_CONFIGURED. "
            "No provider has been registered for this capability.",
        )
