"""Minimal safe filesystem capability for verified file creation."""
from __future__ import annotations

import json
from pathlib import Path

from agent.verification.filesystem import verify_file_exists
from security.audit import record


def create_file(parameters: dict, **_) -> str:
    params = parameters or {}
    path = Path(str(params.get("path", ""))).expanduser()
    if not path.name or path.is_dir():
        return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": "valid file path required"})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(params.get("content", ""))
        path.write_text(content, encoding="utf-8")
        verification = verify_file_exists(str(path), content)
        record(selected_tool="filesystem_create_file", command="create", risk_level="L2",
               confirmation_state="not_required", result=verification.verified,
               exit_code=0 if verification.verified else 1, verification=verification.as_dict())
        return json.dumps({"success": verification.verified, "status": "completed" if verification.verified else "verification_failed",
                           "path": str(path), "file_exists": path.is_file(), "verified": verification.verified,
                           "verification": verification.as_dict()})
    except OSError as exc:
        return json.dumps({"success": False, "status": "failed", "error_category": "permission_denied", "error": str(exc)})


TOOL = {"name": "filesystem_create_file", "description": "Create a local file and verify its path and contents.",
        "risk_level": "L2", "supports_verification": True, "reversible": True,
        "parameters": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "content": {"type": "STRING"}},
                        "required": ["path"]}, "handler": create_file}