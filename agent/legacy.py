from __future__ import annotations

import json


def adapt_legacy_result(value, action: str = "legacy") -> dict:
    """Normalize old string-returning actions without claiming verification."""
    if isinstance(value, dict):
        result = dict(value)
        result.setdefault("action", action)
        result.setdefault("verified", False)
        return result
    try:
        result = json.loads(value)
        if isinstance(result, dict):
            result.setdefault("action", action)
            result.setdefault("verified", False)
            return result
    except (TypeError, json.JSONDecodeError):
        pass
    return {"success": False, "status": "completed_unverified", "action": action,
            "verified": False, "error_category": "legacy_action",
            "error": "Legacy action returned no verifiable structured result.", "output": str(value)}