from __future__ import annotations

import re
from typing import Any

SECRET_RE = re.compile(r"(?i)(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passphrase|secret|credential|cookie|authorization)\s*[:=]\s*[^\s,;}]+")


def redact_text(value: str, *, limit: int | None = None) -> str:
    text = SECRET_RE.sub(r"\1=[REDACTED]", value or "")
    if limit is not None and len(text) > limit:
        return text[:limit] + "\n[TRUNCATED]"
    return text


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if any(token in str(key).lower() for token in ("api_key", "apikey", "token", "password", "secret", "cookie", "authorization")):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
