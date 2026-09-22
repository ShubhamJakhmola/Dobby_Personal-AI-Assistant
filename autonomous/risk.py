"""External action risk classification for the autonomous engine (Phase 19).

Maps high-level action categories to the existing L0-L3 policy levels
defined in security/policy.py.  This module does NOT create a second
policy authority — it translates the autonomous vocabulary into the
existing Dobby policy vocabulary.

Risk category → L-level mapping:
    INFORMATIONAL         → L0  (read-only, no side effects)
    REVERSIBLE_LOCAL      → L1-L2 (local files, local state)
    REVERSIBLE_EXTERNAL   → L2  (external action that can be undone)
    IRREVERSIBLE_EXTERNAL → L3  (requires confirmation)
    SENSITIVE             → L3  (requires confirmation)
"""
from __future__ import annotations

from autonomous.action_contract import RiskLevel


# Map to numeric levels compatible with security.policy L0-L3
_LEVEL_MAP: dict[RiskLevel, int] = {
    RiskLevel.INFORMATIONAL: 0,
    RiskLevel.REVERSIBLE_LOCAL: 1,
    RiskLevel.REVERSIBLE_EXTERNAL: 2,
    RiskLevel.IRREVERSIBLE_EXTERNAL: 3,
    RiskLevel.SENSITIVE: 3,
}

# Risk categories that always require explicit user confirmation
_CONFIRMATION_REQUIRED: frozenset[RiskLevel] = frozenset({
    RiskLevel.IRREVERSIBLE_EXTERNAL,
    RiskLevel.SENSITIVE,
})


def classify_action(capability: str, action: str, parameters: dict | None = None) -> RiskLevel:
    """Classify an autonomous action into a RiskLevel.

    Args:
        capability: e.g. "EMAIL", "BROWSER", "TERMINAL", "PHONE"
        action:     e.g. "email.send", "browser.navigate", "call.start"
        parameters: action parameters (used for heuristics)

    Returns:
        RiskLevel appropriate for this action.
    """
    cap = capability.upper()
    act = action.lower()
    params = parameters or {}

    # Heuristic for secrets / sensitive data in parameters
    for k in params.keys():
        if any(sec in str(k).lower() for sec in ("api_key", "secret", "password", "token", "private_key")):
            return RiskLevel.SENSITIVE

    # ── Phone ────────────────────────────────────────────────────────────
    if cap == "PHONE" or act.startswith("call."):
        return RiskLevel.IRREVERSIBLE_EXTERNAL

    # ── Email ────────────────────────────────────────────────────────────
    if cap == "EMAIL":
        if act in {"email.send", "email.reply"}:
            return RiskLevel.IRREVERSIBLE_EXTERNAL
        if act in {"email.draft", "email.search", "email.read"}:
            return RiskLevel.REVERSIBLE_LOCAL
        return RiskLevel.REVERSIBLE_EXTERNAL

    # ── Messaging ────────────────────────────────────────────────────────
    if cap == "MESSAGING":
        if act in {"message.send", "message.reply"}:
            return RiskLevel.IRREVERSIBLE_EXTERNAL
        if act in {"message.draft", "message.read", "message.search"}:
            return RiskLevel.REVERSIBLE_LOCAL
        return RiskLevel.REVERSIBLE_EXTERNAL

    # ── Browser ──────────────────────────────────────────────────────────
    if cap == "BROWSER":
        if act in {"browser.fill_form", "browser.submit"}:
            return RiskLevel.REVERSIBLE_EXTERNAL
        if act in {"browser.download", "browser.upload"}:
            return RiskLevel.REVERSIBLE_LOCAL
        return RiskLevel.INFORMATIONAL

    # ── Terminal ─────────────────────────────────────────────────────────
    if cap == "TERMINAL":
        # delegate to existing security.policy for terminal commands
        from security.policy import classify as policy_classify
        command = params.get("command", [])
        decision = policy_classify("terminal_execute", {"command": command})
        if decision.level >= 3:
            return RiskLevel.SENSITIVE
        if decision.level >= 2:
            return RiskLevel.REVERSIBLE_LOCAL
        return RiskLevel.INFORMATIONAL

    # ── Filesystem ───────────────────────────────────────────────────────
    if cap == "FILESYSTEM":
        operation = str(params.get("operation", "read")).lower()
        if operation in {"delete", "destroy", "remove", "wipe"}:
            return RiskLevel.SENSITIVE
        if operation in {"write", "create", "edit"}:
            return RiskLevel.REVERSIBLE_LOCAL
        return RiskLevel.INFORMATIONAL

    # ── Coding agent ─────────────────────────────────────────────────────
    if cap == "CODING_AGENT":
        return RiskLevel.REVERSIBLE_LOCAL

    # ── MCP ──────────────────────────────────────────────────────────────
    if cap == "MCP":
        tool_class = str(params.get("tool_class", "read")).lower()
        if tool_class in {"write", "execute", "admin"}:
            return RiskLevel.REVERSIBLE_EXTERNAL
        return RiskLevel.INFORMATIONAL

    # ── Web / research (read-only) ───────────────────────────────────────
    if cap in {"WEB", "WEB_RESEARCH"}:
        return RiskLevel.INFORMATIONAL

    # ── Job application ─────────────────────────────────────────────────
    if cap == "JOB_APPLICATION":
        if act == "application.submit":
            return RiskLevel.IRREVERSIBLE_EXTERNAL
        return RiskLevel.REVERSIBLE_LOCAL

    # ── Calendar ─────────────────────────────────────────────────────────
    if cap == "CALENDAR":
        if act in {"calendar.delete", "calendar.cancel"}:
            return RiskLevel.REVERSIBLE_EXTERNAL
        return RiskLevel.REVERSIBLE_LOCAL

    return RiskLevel.INFORMATIONAL


def requires_confirmation(risk: RiskLevel) -> bool:
    """Return True if this risk level requires explicit user confirmation."""
    return risk in _CONFIRMATION_REQUIRED


def policy_level(risk: RiskLevel) -> int:
    """Convert RiskLevel to Dobby L0-L3 integer level."""
    return _LEVEL_MAP.get(risk, 0)


def categorize_action(action_or_capability: str, parameters: dict | None = None) -> RiskLevel:
    """Convenience single-argument or 2-argument wrapper for classify_action."""
    return classify_action(action_or_capability, action_or_capability, parameters)
