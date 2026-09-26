from __future__ import annotations


def can_integrate(candidate) -> tuple[bool, str]:
    evaluation = candidate.evaluation or {}
    if candidate.status not in {"APPROVED", "ADAPTED"}:
        return False, "candidate must be explicitly approved before integration"
    if evaluation.get("security", {}).get("status") == "REVIEW_REQUIRED":
        return False, "security review is required"
    return True, "candidate is approved for adapter review"