from __future__ import annotations

from acquisition.dependencies import inspect_dependencies
from acquisition.license import inspect_license
from acquisition.security import inspect_security


def evaluate_candidate(candidate, files: dict[str, str], root) -> dict:
    evaluation = {"license": inspect_license(files, candidate.license),
                  "dependencies": inspect_dependencies(root),
                  "security": inspect_security(files),
                  "sandbox": {"strength": "workspace_only", "status": "not_run"},
                  "tests": {"status": "not_run"},
                  "integration": {"status": "review_required"}}
    candidate.evaluation = evaluation
    return evaluation