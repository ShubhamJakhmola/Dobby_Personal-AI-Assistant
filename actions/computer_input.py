from __future__ import annotations

import json
import re

from computer.linux import keyboard, mouse


def computer_input(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "position")).lower()
    try:
        if operation == "position":
            data = mouse.position()
        elif operation == "move":
            data = mouse.move(params["x"], params["y"], params.get("duration", 0))
        elif operation in {"click", "double_click", "right_click", "middle_click"}:
            button = {"right_click": "right", "middle_click": "middle"}.get(operation, "left")
            data = mouse.click(params.get("x"), params.get("y"), button, 2 if operation == "double_click" else 1)
        elif operation == "type":
            data = keyboard.type_text(params.get("text", ""), params.get("interval", 0.02))
        elif operation == "press":
            data = keyboard.press(params["key"])
        elif operation == "hotkey":
            data = keyboard.hotkey(params["keys"])
        else:
            return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": "unsupported input operation"})
        return json.dumps({"success": True, "status": "completed", "operation": operation, "data": data, "verified": operation == "position"})
    except KeyError as exc:
        return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": f"missing parameter: {exc.args[0]}"})
    except Exception as exc:
        return json.dumps({"success": False, "status": "failed", "error_category": "backend_unavailable", "error": str(exc)})


TOOL = {"name": "computer_input", "description": "Control the Linux mouse and keyboard for normal desktop interaction.",
        "risk_level": "L1", "supports_verification": True, "reversible": True,
        "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING"}, "x": {"type": "NUMBER"}, "y": {"type": "NUMBER"}, "duration": {"type": "NUMBER"}, "text": {"type": "STRING"}, "key": {"type": "STRING"}, "keys": {"type": "ARRAY", "items": {"type": "STRING"}}}, "required": ["operation"]},
        "handler": computer_input}