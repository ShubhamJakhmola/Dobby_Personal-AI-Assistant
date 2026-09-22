"""Phone / call capability provider — abstraction layer (Phase 19).

Status: NOT_CONFIGURED (no real provider connected yet).

IMPORTANT:
  - Calls are external effects (IRREVERSIBLE_EXTERNAL) → L3 gate.
  - Call target must originate from an authorized user/context; never from
    untrusted web content.
  - If call recording/transcription is ever added, that is a separate
    sensitive capability.

Call lifecycle states:
  CALL_REQUESTED → DIALING → CONNECTED → ENDED / FAILED
"""
from __future__ import annotations

import logging
from typing import Any

from autonomous.action_contract import ActionRequest, ActionResult
from capabilities.base import CapabilityProvider, CapabilityStatus

logger = logging.getLogger(__name__)

PHONE_ACTIONS = {
    "call.start",
    "call.end",
    "call.status",
    "call.hold",
    "call.resume",
    "call.transfer",
}

CALL_STATES = {
    "CALL_REQUESTED",
    "DIALING",
    "CONNECTED",
    "ENDED",
    "FAILED",
}


class PhoneCapabilityProvider(CapabilityProvider):
    """Phone / call capability abstraction.

    Currently NOT_CONFIGURED.  Inject a connector (VoIP, SIP, Twilio, etc.)
    to activate.  Not all machines can make phone calls; capability discovery
    is used to determine availability.
    """

    name = "phone"

    def __init__(self, connector=None):
        self._connector = connector
        self._active_calls: dict[str, str] = {}   # call_id → state

    def status(self) -> str:
        if self._connector is not None:
            try:
                return self._connector.health()
            except Exception:
                return CapabilityStatus.ERROR
        return CapabilityStatus.NOT_CONFIGURED

    def execute(self, request: ActionRequest) -> ActionResult:
        action = request.parameters.get("action") or request.capability

        if action not in PHONE_ACTIONS:
            return ActionResult.fail(
                request.action_id,
                f"Unsupported phone action: {action!r}. "
                f"Supported: {sorted(PHONE_ACTIONS)}",
            )

        if self._connector is None:
            from autonomous.action_contract import ActionStatus
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.NOT_CONFIGURED,
                error="Phone capability is NOT_CONFIGURED. Connect a VoIP/telephony provider to enable.",
            )

        # Safety: target must be explicit in parameters
        target = request.parameters.get("target") or request.parameters.get("number")
        if action == "call.start" and not target:
            return ActionResult.fail(
                request.action_id,
                "call.start requires an explicit 'target' number in parameters. "
                "Dobby will not infer a call target from web content.",
            )

        try:
            result = self._connector.execute(action, request.parameters)
            # Track state
            call_id = result.get("call_id", request.action_id)
            state = result.get("state", "CALL_REQUESTED")
            self._active_calls[call_id] = state
            return ActionResult.ok(
                request.action_id,
                output=result,
                external_reference=str(call_id),
            )
        except Exception as exc:
            logger.exception("Phone action %s failed", action)
            return ActionResult.fail(request.action_id, str(exc))

    def active_calls(self) -> dict[str, str]:
        return dict(self._active_calls)

    def supported_actions(self) -> list[str]:
        return sorted(PHONE_ACTIONS)
