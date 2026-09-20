from __future__ import annotations

from security.audit import record


def record_mcp_event(**fields):
    safe = {key: value for key, value in fields.items() if key not in {"secret", "token", "password", "api_key", "private_key"}}
    record(selected_tool="mcp", **safe)
