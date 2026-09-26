from __future__ import annotations

import re

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.I),
    re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passphrase|secret|credential|session[_ -]?token)\b\s*[:=]", re.I),
    re.compile(r"\b(?:sk|ghp|glpat|xox[baprs])-[-_A-Za-z0-9]{12,}\b", re.I),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
)


def secret_reason(value: object) -> str:
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return "secret-like value"
    return ""


def is_sensitive(value: object) -> bool:
    return bool(secret_reason(value))


def sanitize(value: object, replacement: str = "[REDACTED]") -> str:
    text = str(value or "")
    return replacement if is_sensitive(text) else text