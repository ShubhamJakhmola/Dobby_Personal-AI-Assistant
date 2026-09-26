"""Universal Recovery Engine for the autonomous execution loop (Phase 19).

Classifies failures and selects the appropriate recovery strategy.
Bounded retries prevent infinite loops.
"""
from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    AUTHENTICATION = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    VALIDATION = "VALIDATION"
    DEPENDENCY = "DEPENDENCY"
    NETWORK = "NETWORK"
    TOOL = "TOOL"
    ENVIRONMENT = "ENVIRONMENT"
    UNKNOWN = "UNKNOWN"


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    BACKOFF = "backoff"
    ALTERNATIVE_CAPABILITY = "alternative_capability"
    ALTERNATIVE_PROVIDER = "alternative_provider"
    REPAIR = "repair"
    REPLAN = "replan"
    ASK_USER = "ask_user"
    ABORT = "abort"


# Failure keyword → category mapping (ordered, first match wins)
_CLASSIFIERS: list[tuple[list[str], FailureCategory]] = [
    (["401", "403", "authentication", "unauthenticated", "auth", "login", "credentials"],
     FailureCategory.AUTHENTICATION),
    (["permission", "denied", "policy_denied", "not allowed", "unauthorized"],
     FailureCategory.PERMISSION),
    (["invalid", "validation", "bad parameter", "schema", "missing required"],
     FailureCategory.VALIDATION),
    (["dependency", "prerequisite", "dependency_failed"],
     FailureCategory.DEPENDENCY),
    (["timeout", "connection", "network", "dns", "unreachable", "econnrefused", "transient"],
     FailureCategory.TRANSIENT),
    (["not found", "tool not found", "unknown action", "capability unavailable"],
     FailureCategory.TOOL),
    (["environment", "not installed", "not configured", "missing binary"],
     FailureCategory.ENVIRONMENT),
    (["error", "exception", "crash"],
     FailureCategory.TRANSIENT),
]

# Category → preferred recovery strategy
_STRATEGY_MAP: dict[FailureCategory, RecoveryStrategy] = {
    FailureCategory.TRANSIENT: RecoveryStrategy.RETRY,
    FailureCategory.AUTHENTICATION: RecoveryStrategy.ASK_USER,
    FailureCategory.PERMISSION: RecoveryStrategy.ASK_USER,
    FailureCategory.VALIDATION: RecoveryStrategy.REPAIR,
    FailureCategory.DEPENDENCY: RecoveryStrategy.REPLAN,
    FailureCategory.NETWORK: RecoveryStrategy.BACKOFF,
    FailureCategory.TOOL: RecoveryStrategy.ALTERNATIVE_CAPABILITY,
    FailureCategory.ENVIRONMENT: RecoveryStrategy.ABORT,
    FailureCategory.UNKNOWN: RecoveryStrategy.RETRY,
}


def classify_failure(error: str) -> FailureCategory:
    """Classify an error string into a FailureCategory."""
    error_lower = str(error or "").lower()
    for keywords, category in _CLASSIFIERS:
        if any(kw in error_lower for kw in keywords):
            return category
    return FailureCategory.UNKNOWN


def select_strategy(category: FailureCategory) -> RecoveryStrategy:
    return _STRATEGY_MAP.get(category, RecoveryStrategy.RETRY)


class RecoveryEngine:
    """Decides and executes recovery for a failed GoalTask.

    The engine is strategy-first: it classifies the failure, picks a
    strategy, and only actually retries if that strategy is viable given
    the task's retry policy.  It never retries indefinitely.
    """

    def __init__(self, capability_router=None, confirmation_callback=None):
        self._router = capability_router
        self._confirm = confirmation_callback   # callable(task, reason) → bool

    def classify_and_select(self, task_or_id: Any, error_message: str):
        from dataclasses import dataclass
        @dataclass
        class Selection:
            category: FailureCategory
            strategy: RecoveryStrategy

        cat = classify_failure(error_message)
        strat = select_strategy(cat)
        return Selection(category=cat, strategy=strat)

    def recover(
        self,
        task: Any,          # GoalTask
        result: Any,        # ActionResult
        attempt: int = 1,
    ) -> tuple[RecoveryStrategy, dict]:
        """Return (strategy_chosen, recovery_metadata).

        The caller decides whether to actually execute the strategy.
        This method handles BACKOFF sleep, strategy selection, and logging.

        Returns:
            (strategy, metadata_dict) — caller interprets 'replan' / 'ask_user'
            signals and acts accordingly.
        """
        error = result.error if hasattr(result, "error") else str(result)
        category = classify_failure(error)
        strategy = select_strategy(category)
        max_retries = getattr(getattr(task, "retry_policy", None), "max_retries", 3)
        backoff = getattr(getattr(task, "retry_policy", None), "backoff_seconds", 2.0)
        alt_cap = getattr(getattr(task, "retry_policy", None), "alternative_capability", "")

        metadata = {
            "attempt": attempt,
            "category": category.value,
            "strategy": strategy.value,
            "max_retries": max_retries,
            "error": error,
        }

        logger.info(
            "Recovery attempt %d for task %s: category=%s strategy=%s",
            attempt,
            getattr(task, "task_id", "?"),
            category.value,
            strategy.value,
        )

        # ── Guard: do not exceed retry limit ─────────────────────────────
        if attempt >= max_retries:
            metadata["strategy"] = RecoveryStrategy.REPLAN.value
            metadata["reason"] = "retry_limit_exceeded"
            return RecoveryStrategy.REPLAN, metadata

        # ── Strategy-specific logic ───────────────────────────────────────
        if strategy == RecoveryStrategy.BACKOFF:
            sleep_for = backoff * (2 ** (attempt - 1))
            metadata["sleep_seconds"] = sleep_for
            time.sleep(sleep_for)
            return RecoveryStrategy.BACKOFF, metadata

        if strategy == RecoveryStrategy.ALTERNATIVE_CAPABILITY and alt_cap:
            metadata["alternative_capability"] = alt_cap
            return RecoveryStrategy.ALTERNATIVE_CAPABILITY, metadata

        if strategy == RecoveryStrategy.ASK_USER:
            if self._confirm:
                approved = self._confirm(task, f"Recovery needed: {error}")
                if approved:
                    return RecoveryStrategy.RETRY, {**metadata, "user_approved": True}
            return RecoveryStrategy.ASK_USER, metadata

        if strategy == RecoveryStrategy.REPLAN:
            return RecoveryStrategy.REPLAN, metadata

        if strategy in {RecoveryStrategy.RETRY, RecoveryStrategy.REPAIR}:
            return strategy, metadata

        return RecoveryStrategy.ABORT, metadata
