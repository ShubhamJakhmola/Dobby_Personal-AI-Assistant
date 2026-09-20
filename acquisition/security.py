from __future__ import annotations

import re

SUSPICIOUS = re.compile(r"(?:sudo|rm\s+-rf|curl\s+.*\|\s*(?:sh|bash)|wget\s+.*\|\s*(?:sh|bash)|/\.ssh|id_rsa|os\.environ|chmod\s+\+s|chown\s+root)", re.I)


def inspect_security(files: dict[str, str]) -> dict:
    findings = []
    for name, content in files.items():
        match = SUSPICIOUS.search(content)
        if match: findings.append({"file": name, "evidence": match.group(0)})
    return {"status": "REVIEW_REQUIRED" if findings else "CLEAR", "findings": findings,
            "disclaimer": "static inspection is not proof of safety"}