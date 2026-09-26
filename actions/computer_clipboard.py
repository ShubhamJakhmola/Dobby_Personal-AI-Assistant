from __future__ import annotations

import json

from computer.linux import clipboard
from security.audit import record


def computer_clipboard(parameters: dict, **_) -> str:
    operation = str((parameters or {}).get("operation", "get")).lower()
    try:
        if operation == "get":
            data = clipboard.get()
            record(selected_tool="computer_clipboard", command="get", risk_level="L0", result=True,
                   clipboard_length=data["length"], clipboard_redacted=True)
        elif operation == "set":
            text = str((parameters or {}).get("text", ""))
            data = clipboard.set_text(text)
            record(selected_tool="computer_clipboard", command="set", risk_level="L1", result=True,
                   clipboard_length=len(text), clipboard_redacted=True)
        elif operation == "clear":
            data = clipboard.clear()
            record(selected_tool="computer_clipboard", command="clear", risk_level="L1", result=True)
        else:
            return json.dumps({"success": False, "error_category": "invalid_arguments", "error": "supported operations: get, set, clear"})
        return json.dumps({"success": True, "status": "completed", "operation": operation, "data": data, "verified": True})
    except Exception as exc:
        return json.dumps({"success": False, "status": "failed", "error_category": "backend_unavailable", "error": str(exc)})


TOOL = {"name": "computer_clipboard", "description": "Read, set, or clear the local clipboard with redacted audit records.",
        "risk_level": "L1", "supports_verification": True, "reversible": True,
        "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING"}, "text": {"type": "STRING"}}, "required": ["operation"]},
        "handler": computer_clipboard}