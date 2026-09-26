"""Abstract base for all Dobby capability providers (Phase 19).

Every provider — browser, email, messaging, phone, MCP, coding agent,
terminal, filesystem, etc. — implements this interface.  The CapabilityRouter
dispatches ActionRequests through it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from autonomous.action_contract import ActionRequest, ActionResult


class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    REQUIRES_AUTH = "REQUIRES_AUTH"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    ERROR = "ERROR"


class CapabilityProvider(ABC):
    """Abstract capability provider.

    Subclasses must implement `name`, `status()`, and `execute()`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier string."""

    @abstractmethod
    def status(self) -> str:
        """Return a CapabilityStatus string."""

    @abstractmethod
    def execute(self, request: ActionRequest) -> ActionResult:
        """Execute the action described by request."""

    def is_available(self) -> bool:
        return self.status() == CapabilityStatus.AVAILABLE

    def describe(self) -> dict:
        return {
            "provider": self.name,
            "status": self.status(),
            "available": self.is_available(),
        }
