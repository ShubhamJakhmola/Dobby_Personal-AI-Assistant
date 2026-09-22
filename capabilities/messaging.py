"""Messaging capability provider — abstraction layer (Phase 19).

Status: NOT_CONFIGURED (no real provider connected yet).

Possible providers: WhatsApp, Telegram, SMS, Slack, Teams, Discord.
Provider selection is done via the 'provider' field in ActionRequest.

IMPORTANT:
  - Reading / drafting: lower risk
  - Sending externally: L3 gate (IRREVERSIBLE_EXTERNAL)
  - Dobby must not invent facts in messages.
"""
from __future__ import annotations

import logging
from typing import Any

from autonomous.action_contract import ActionRequest, ActionResult
from capabilities.base import CapabilityProvider, CapabilityStatus

logger = logging.getLogger(__name__)

MESSAGING_ACTIONS = {
    "message.search", "messaging.search",
    "message.read", "messaging.read",
    "message.draft", "messaging.draft",
    "message.send", "messaging.send",
    "message.reply", "messaging.reply",
    "message.list_chats", "messaging.list_chats",
    "message.delete", "messaging.delete",
}

MESSAGING_PROVIDERS = {
    "whatsapp", "telegram", "sms", "slack", "teams", "discord",
}


class MessagingCapabilityProvider(CapabilityProvider):
    """Messaging capability abstraction.

    Currently NOT_CONFIGURED.  Inject a connector to activate.
    """

    name = "messaging"

    def __init__(self, connectors: dict | None = None):
        """Args:
            connectors: dict mapping provider name → connector object.
        """
        self._connectors: dict[str, Any] = connectors or {}

    def status(self) -> str:
        if self._connectors:
            return CapabilityStatus.AVAILABLE
        return CapabilityStatus.NOT_CONFIGURED

    def execute(self, request: ActionRequest) -> ActionResult:
        action = request.parameters.get("action") or request.capability
        provider_name = (request.provider or "").lower()

        if action not in MESSAGING_ACTIONS:
            return ActionResult.fail(
                request.action_id,
                f"Unsupported messaging action: {action!r}. "
                f"Supported: {sorted(MESSAGING_ACTIONS)}",
            )

        connector = self._connectors.get(provider_name)
        if connector is None:
            from autonomous.action_contract import ActionStatus
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.NOT_CONFIGURED,
                error=f"Messaging provider '{provider_name or 'any'}' is NOT_CONFIGURED. Available providers: {sorted(self._connectors.keys()) or 'none'}",
            )

        try:
            result = connector.execute(action, request.parameters)
            return ActionResult.ok(request.action_id, output=result)
        except Exception as exc:
            logger.exception("Messaging action %s via %s failed", action, provider_name)
            return ActionResult.fail(request.action_id, str(exc))

    def available_providers(self) -> list[str]:
        return list(self._connectors.keys())

    def supported_actions(self) -> list[str]:
        return sorted(MESSAGING_ACTIONS)
