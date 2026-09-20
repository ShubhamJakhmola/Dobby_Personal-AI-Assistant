from __future__ import annotations

import re
import uuid

from acquisition.models import CapabilityRequest, CandidateRepository


class CapabilityGapAnalyzer:
    def __init__(self, action_registry):
        self.action_registry = action_registry

    def existing(self, name: str) -> bool:
        normalized = name.lower().replace(".", "_")
        return normalized in {item.lower() for item in self.action_registry.names()}

    def analyze(self, name: str, description: str = "", operations: list[str] | None = None) -> dict:
        if self.existing(name):
            return {"missing": False, "status": "available", "reason": "existing registered capability"}
        request = CapabilityRequest(str(uuid.uuid4()), name, description, operations or [])
        return {"missing": True, "status": "capability_missing", "request": request.as_dict()}


def candidate_from_github(payload: dict) -> CandidateRepository:
    license_info = payload.get("license") or {}
    return CandidateRepository(
        candidate_id=str(payload.get("id") or uuid.uuid4()),
        name=payload.get("name", ""), owner=(payload.get("owner") or {}).get("login", ""),
        url=payload.get("html_url", ""), description=payload.get("description", "") or "",
        language=payload.get("language", "") or "", license=license_info.get("spdx_id", "") or "",
        default_branch=payload.get("default_branch", ""), last_activity=payload.get("updated_at", ""),
        stars=int(payload.get("stargazers_count", 0) or 0), forks=int(payload.get("forks_count", 0) or 0),
    )