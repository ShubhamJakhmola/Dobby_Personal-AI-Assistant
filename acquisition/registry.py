from __future__ import annotations

import json
from pathlib import Path

from acquisition.models import CandidateStatus
from memory.storage import memory_root, read_json, write_json
from security.audit import record


class AcquisitionRegistry:
    def __init__(self, root=None):
        self.path = memory_root(root) / "acquisition_candidates.json"

    def list(self) -> list[dict]:
        data = read_json(self.path, {})
        return list(data.values()) if isinstance(data, dict) else []

    def save(self, candidate) -> None:
        data = read_json(self.path, {})
        data[candidate.candidate_id] = candidate.as_dict()
        write_json(self.path, data)

    def transition(self, candidate, status: str) -> dict:
        allowed = {CandidateStatus.DISCOVERED: {CandidateStatus.INSPECTING, CandidateStatus.REJECTED},
                   CandidateStatus.INSPECTING: {CandidateStatus.SANDBOXED, CandidateStatus.REJECTED, CandidateStatus.FAILED},
                   CandidateStatus.SANDBOXED: {CandidateStatus.TESTING, CandidateStatus.REJECTED},
                   CandidateStatus.TESTING: {CandidateStatus.APPROVED, CandidateStatus.REJECTED, CandidateStatus.FAILED},
                   CandidateStatus.APPROVED: {CandidateStatus.ADAPTED, CandidateStatus.REGISTERED},
                   CandidateStatus.ADAPTED: {CandidateStatus.REGISTERED}}
        if status not in allowed.get(candidate.status, set()):
            raise ValueError(f"invalid candidate transition: {candidate.status} -> {status}")
        candidate.status = status
        self.save(candidate)
        record(selected_tool="acquisition", command=f"candidate_{status.lower()}", candidate_id=candidate.candidate_id, result=True)
        return candidate.as_dict()