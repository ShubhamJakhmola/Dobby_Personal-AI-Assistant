"""Capability providers package (Phase 19).

Each provider implements the CapabilityProvider interface defined in base.py.
Providers are registered with the CapabilityRouter at startup.
"""
from __future__ import annotations

from capabilities.base import CapabilityProvider, CapabilityStatus

__all__ = ["CapabilityProvider", "CapabilityStatus"]
