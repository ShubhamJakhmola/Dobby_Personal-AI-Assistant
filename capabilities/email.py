"""Email capability provider — abstraction layer (Phase 19).

Status: NOT_CONFIGURED (no real provider connected yet).
The full interface is defined so real connectors can be plugged in
(Gmail API, IMAP/SMTP, Outlook, etc.) without changing the orchestration layer.

IMPORTANT:
  - Reading email: lower risk (REVERSIBLE_LOCAL)
  - Drafting: lower risk (REVERSIBLE_LOCAL)
  - Sending externally: L3 policy gate (IRREVERSIBLE_EXTERNAL)
    → handled by CapabilityRouter confirmation logic
  - Dobby must never fabricate facts in outgoing messages.
"""
from __future__ import annotations

import logging
from typing import Any

from autonomous.action_contract import ActionRequest, ActionResult
from capabilities.base import CapabilityProvider, CapabilityStatus

logger = logging.getLogger(__name__)

# Full email capability surface
EMAIL_ACTIONS = {
    "email.search",
    "email.read",
    "email.draft",
    "email.send",
    "email.reply",
    "email.attach",
    "email.list_folders",
    "email.move",
    "email.delete",
}


class EmailCapabilityProvider(CapabilityProvider):
    """Email capability abstraction.

    Currently NOT_CONFIGURED.  Subclass or inject a connector to activate.
    """

    name = "email"

    def __init__(self, connector=None):
        self._connector = connector

    def status(self) -> str:
        if self._connector is not None:
            try:
                return self._connector.health()
            except Exception:
                return CapabilityStatus.ERROR
        return CapabilityStatus.NOT_CONFIGURED

    def execute(self, request: ActionRequest) -> ActionResult:
        action = request.parameters.get("action") or request.capability

        if action not in EMAIL_ACTIONS:
            return ActionResult.fail(
                request.action_id,
                f"Unsupported email action: {action!r}. Supported: {sorted(EMAIL_ACTIONS)}",
            )

        if self._connector is None:
            from autonomous.action_contract import ActionStatus
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.NOT_CONFIGURED,
                error="Email capability is NOT_CONFIGURED. Connect an email provider (Gmail, IMAP/SMTP, Outlook) to enable.",
            )

        try:
            result = self._connector.execute(action, request.parameters)
            return ActionResult.ok(request.action_id, output=result)
        except Exception as exc:
            logger.exception("Email action %s failed", action)
            return ActionResult.fail(request.action_id, str(exc))

    def supported_actions(self) -> list[str]:
        return sorted(EMAIL_ACTIONS)
