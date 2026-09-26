from __future__ import annotations
import json
from computer import desktop

def computer_input(parameters: dict, **_) -> str:
    p = parameters or {}; op = str(p.get("operation", "position")).lower()
    try:
        if op in {"position", "move", "click", "double_click", "right_click", "middle_click"}:
            data = desktop.mouse(op, **p)
        elif op in {"type", "press", "hotkey"}:
            data = desktop.keyboard(op, **p)
        else:
            return json.dumps({"success": False, "status":"failed", "error_category":"invalid_arguments"})
        return json.dumps(data | {"operation": op, "status": "completed" if data.get("success") else "failed"})
    except Exception as exc:
        return json.dumps({"success":False,"status":"failed","error_category":"backend_unavailable","error":str(exc)})

TOOL={"name":"computer_input","description":"Cross-platform mouse and keyboard control.","risk_level":"L1","supports_verification":True,"reversible":True,
"parameters":{"type":"OBJECT","properties":{"operation":{"type":"STRING"},"x":{"type":"NUMBER"},"y":{"type":"NUMBER"},"duration":{"type":"NUMBER"},"text":{"type":"STRING"},"key":{"type":"STRING"},"keys":{"type":"ARRAY","items":{"type":"STRING"}}},"required":["operation"]},"handler":computer_input}
