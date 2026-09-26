from __future__ import annotations

from acquisition.models import CandidateStatus


def approve(candidate, registry) -> dict:
    if candidate.status != CandidateStatus.TESTING:
        return {"success": False, "error_category": "invalid_state", "error": "candidate must pass through testing before approval"}
    registry.transition(candidate, CandidateStatus.APPROVED)
    return {"success": True, "status": candidate.status, "candidate": candidate.as_dict()}


def reject(candidate, registry, reason: str = "") -> dict:
    if candidate.status == CandidateStatus.REGISTERED:
        return {"success": False, "error_category": "invalid_state", "error": "registered candidate cannot be rejected by this operation"}
    candidate.evaluation = {**candidate.evaluation, "rejection_reason": reason}
    candidate.status = CandidateStatus.REJECTED
    registry.save(candidate)
    return {"success": True, "status": candidate.status, "candidate": candidate.as_dict()}