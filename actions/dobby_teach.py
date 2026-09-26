"""User-teachable workflow memory for Dobby."""
from __future__ import annotations

import json
from memory.skill_library import find_skill, list_skills, save_skill


def dobby_teach(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "teach")).lower().strip()
    if operation == "teach":
        name = str(params.get("name", "")).strip()
        trigger = str(params.get("trigger", "")).strip()
        steps = params.get("steps", [])
        if not name or not trigger or not isinstance(steps, list) or not steps:
            return json.dumps({"success": False, "error": "Teach requires name, trigger, and a non-empty steps array."})
        return json.dumps({"success": True, "skill": save_skill(name, trigger, steps, str(params.get("notes", "")))}, ensure_ascii=False)
    if operation == "list":
        return json.dumps({"skills": list_skills()}, ensure_ascii=False)
    if operation == "find":
        return json.dumps({"skills": find_skill(str(params.get("query", "")), int(params.get("limit", 5)))}, ensure_ascii=False)
    return json.dumps({"success": False, "error": "Supported operations: teach, list, find."})


TOOL = {
    "name": "dobby_teach",
    "description": "Store and retrieve user-taught workflows as reusable procedures. Taught procedures are memory, not executable code; executable third-party skills still require acquisition/security review.",
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING"},
        "name": {"type": "STRING"},
        "trigger": {"type": "STRING"},
        "steps": {"type": "ARRAY", "items": {"type": "STRING"}},
        "notes": {"type": "STRING"},
        "query": {"type": "STRING"},
        "limit": {"type": "NUMBER"},
    }, "required": ["operation"]},
    "handler": dobby_teach,
    "risk_level": "L1",
    "reversible": True,
    "supports_verification": True,
}
