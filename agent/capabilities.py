from __future__ import annotations

import re


class CapabilitySelector:
    """Selects from discovered metadata by generic token relevance."""

    def select(self, intent, registry):
        requested = set(re.findall(r"[a-z0-9]+", intent.intent.lower()))
        requested.update(re.findall(r"[a-z0-9]+", str(intent.parameters.get("operation", "")).lower()))
        best = None
        best_score = 0
        for name in registry.names():
            metadata = registry.metadata(name)
            words = set(re.findall(r"[a-z0-9]+", f"{name} {metadata.get('description', '')}".lower()))
            score = len(requested & words)
            if name.replace("_", ".") == intent.intent:
                score += 100
            if score > best_score:
                best, best_score = name, score
        return best

    def list_capabilities(self, registry) -> list[dict]:
        return [registry.metadata(name) for name in sorted(registry.names())]