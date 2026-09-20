from __future__ import annotations

from dataclasses import asdict


def adapter_metadata(candidate) -> dict:
    return {"capability": "", "candidate_id": candidate.candidate_id, "source": candidate.url,
            "commit_sha": candidate.commit_sha, "license": candidate.license,
            "runtime": candidate.dependencies.get("runtime", "unknown"),
            "verified": candidate.status == "APPROVED", "location": candidate.candidate_path}