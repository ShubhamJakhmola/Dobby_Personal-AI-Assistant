from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from acquisition.adapter import adapter_metadata
from acquisition.discovery import CapabilityGapAnalyzer
from acquisition.evaluators import evaluate_candidate
from acquisition.github import GitHubClient
from acquisition.lifecycle import approve, reject
from acquisition.models import CandidateRepository, CandidateStatus
from acquisition.registry import AcquisitionRegistry
from acquisition.sandbox import Sandbox


class AcquisitionManager:
    def __init__(self, action_registry, *, github=None, registry=None, sandbox=None):
        self.gaps = CapabilityGapAnalyzer(action_registry)
        self.github = github or GitHubClient()
        self.registry = registry or AcquisitionRegistry()
        self.sandbox = sandbox or Sandbox()

    def search(self, capability: str, description: str = "") -> dict:
        gap = self.gaps.analyze(capability, description)
        if not gap["missing"]:
            return gap
        return {**gap, "discovery": self.github.search(description or capability)}

    def inspect(self, candidate: CandidateRepository, files: dict[str, str], root: str | Path) -> dict:
        if candidate.status == CandidateStatus.DISCOVERED:
            self.registry.transition(candidate, CandidateStatus.INSPECTING)
        evaluation = evaluate_candidate(candidate, files, root)
        self.registry.save(candidate)
        return {"success": True, "candidate": candidate.as_dict(), "evaluation": evaluation}

    def dry_run(self, capability: str, description: str = "") -> dict:
        result = self.search(capability, description)
        result["dry_run"] = True
        result["side_effects"] = []
        return result

    def approve(self, candidate: CandidateRepository) -> dict:
        return approve(candidate, self.registry)

    def reject(self, candidate: CandidateRepository, reason: str = "") -> dict:
        return reject(candidate, self.registry, reason)

    def cleanup(self) -> dict:
        root = self.sandbox.root
        removed = 0
        if root.exists():
            for child in root.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                    removed += 1
        return {"success": True, "removed_workspaces": removed}

    def register_adapter(self, candidate: CandidateRepository, capability: str) -> dict:
        if candidate.status != CandidateStatus.APPROVED:
            return {"success": False, "error_category": "approval_required", "error": "candidate must be approved"}
        candidate.status = CandidateStatus.REGISTERED
        self.registry.save(candidate)
        metadata = adapter_metadata(candidate); metadata["capability"] = capability
        return {"success": True, "status": candidate.status, "adapter": metadata}