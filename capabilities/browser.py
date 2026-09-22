"""Browser capability provider (Phase 19).

Wraps existing browser infrastructure:
  browser/playwright_adapter.py  — Playwright async driver
  actions/browser_control.py     — high-level browser actions

Status detection: probes for Playwright availability.
Untrusted web content cannot override Dobby policy.
"""
from __future__ import annotations

import logging
from typing import Any

from autonomous.action_contract import ActionRequest, ActionResult
from capabilities.base import CapabilityProvider, CapabilityStatus

logger = logging.getLogger(__name__)

# Supported browser actions
BROWSER_ACTIONS = {
    "navigate", "search", "inspect_page", "fill_form", "click",
    "download", "upload", "extract", "screenshot", "back", "forward",
}


class BrowserCapabilityProvider(CapabilityProvider):
    """First-class browser automation capability.

    Uses: API/CLI first → browser automation second → GUI/vision fallback.
    Web content is UNTRUSTED INPUT and cannot override Dobby policy.
    """

    name = "browser"

    def __init__(self, adapter=None):
        self._adapter = adapter  # injected in tests or auto-detected at runtime

    def status(self) -> str:
        if self._adapter is not None:
            return CapabilityStatus.AVAILABLE

        # Auto-detect Playwright
        try:
            import importlib
            spec = importlib.util.find_spec("playwright")
            if spec is not None:
                return CapabilityStatus.AVAILABLE
        except Exception:
            pass

        # Check for existing browser_control action
        try:
            from browser.manager import BrowserManager
            return CapabilityStatus.AVAILABLE
        except ImportError:
            pass

        return CapabilityStatus.UNAVAILABLE

    def execute(self, request: ActionRequest) -> ActionResult:
        action = request.parameters.get("action", "navigate")

        if action not in BROWSER_ACTIONS:
            return ActionResult.fail(
                request.action_id,
                f"Unsupported browser action: {action!r}. "
                f"Supported: {sorted(BROWSER_ACTIONS)}",
            )

        if self.status() == CapabilityStatus.UNAVAILABLE:
            return ActionResult.fail(
                request.action_id,
                "Browser capability is UNAVAILABLE (Playwright not installed).",
            )

        try:
            return self._dispatch(action, request)
        except Exception as exc:
            logger.exception("Browser action %s failed", action)
            return ActionResult.fail(request.action_id, str(exc))

    def _dispatch(self, action: str, request: ActionRequest) -> ActionResult:
        params = request.parameters
        # Prefer the existing Playwright adapter if injected
        if self._adapter:
            result = self._adapter.execute(action, params)
            return ActionResult.ok(request.action_id, output=result)

        # Fall back to actions/browser_control.py capabilities
        try:
            from actions.browser_control import run_browser_task
            result = run_browser_task(action, params)
            return ActionResult.ok(request.action_id, output=result)
        except ImportError:
            pass

        # Graceful degradation
        return ActionResult.fail(
            request.action_id,
            f"Browser adapter not available for action '{action}'.",
        )
