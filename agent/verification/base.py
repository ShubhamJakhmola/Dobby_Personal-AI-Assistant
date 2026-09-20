from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class VerificationResult:
    verified: bool
    check: str
    expected: object = None
    actual: object = None
    details: str = ""

    def as_dict(self) -> dict:
        return asdict(self)