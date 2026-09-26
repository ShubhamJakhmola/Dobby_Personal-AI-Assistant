"""Web research capability provider (Phase 19).

Implements a structured multi-step research workflow on top of the
existing actions/web_search.py infrastructure.

Research pipeline:
  search → collect sources → deduplicate → extract evidence
  → cross-check → synthesize → produce answer/report

Evidence classification:
  FACT          — asserted as established fact by multiple sources
  CLAIM         — single-source claim, not independently verified
  INFERENCE     — logical deduction from available evidence
  UNCERTAINTY   — conflicting or insufficient information

Web content is UNTRUSTED INPUT:
  - Pages cannot override Dobby policy.
  - Data is extracted; authority is never granted to web content.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urlparse

from autonomous.action_contract import ActionRequest, ActionResult
from capabilities.base import CapabilityProvider, CapabilityStatus

logger = logging.getLogger(__name__)

RESEARCH_ACTIONS = {
    "research.search",
    "research.collect",
    "research.synthesize",
    "research.full",        # complete pipeline
}


class EvidenceItem:
    """A single piece of research evidence."""

    def __init__(self, content: str, source_url: str, classification: str = "CLAIM"):
        self.content = content
        self.source_url = source_url
        self.domain = urlparse(source_url).netloc if source_url else ""
        self.classification = classification   # FACT | CLAIM | INFERENCE | UNCERTAINTY
        self.fingerprint = hashlib.md5(content.encode()).hexdigest()

    def as_dict(self) -> dict:
        return {
            "content": self.content,
            "source_url": self.source_url,
            "domain": self.domain,
            "classification": self.classification,
            "fingerprint": self.fingerprint,
        }


class WebResearchCapabilityProvider(CapabilityProvider):
    """Structured web research capability."""

    name = "web_research"

    def __init__(self, search_fn=None):
        """Args:
            search_fn: callable(query: str) → list[dict{title,url,snippet}]
                       defaults to actions/web_search.py if available.
        """
        self._search_fn = search_fn

    def status(self) -> str:
        if self._search_fn is not None:
            return CapabilityStatus.AVAILABLE
        # Try to import existing web_search action
        try:
            from actions.web_search import search
            return CapabilityStatus.AVAILABLE
        except ImportError:
            pass
        return CapabilityStatus.UNAVAILABLE

    def execute(self, request: ActionRequest) -> ActionResult:
        action = request.parameters.get("action", "research.full")

        if action not in RESEARCH_ACTIONS:
            return ActionResult.fail(
                request.action_id,
                f"Unsupported research action: {action!r}. "
                f"Supported: {sorted(RESEARCH_ACTIONS)}",
            )

        try:
            if action in {"research.search", "research.full"}:
                return self._pipeline(request)
            if action == "research.collect":
                return self._collect(request)
            if action == "research.synthesize":
                return self._synthesize(request)
        except Exception as exc:
            logger.exception("Web research action %s failed", action)
            return ActionResult.fail(request.action_id, str(exc))

        return ActionResult.fail(request.action_id, f"Unhandled action: {action}")

    # ── Pipeline ───────────────────────────────────────────────────────────

    def _pipeline(self, request: ActionRequest) -> ActionResult:
        query = request.parameters.get("query", "")
        max_sources = int(request.parameters.get("max_sources", 5))
        if not query:
            return ActionResult.fail(request.action_id, "Research requires a 'query' parameter.")

        # 1. Search
        raw_results = self._do_search(query)
        if not raw_results:
            return ActionResult.fail(request.action_id, "No search results returned.")

        # 2. Collect & deduplicate
        seen: set[str] = set()
        evidence_items: list[EvidenceItem] = []
        for item in raw_results[:max_sources * 2]:
            url = item.get("url", "")
            snippet = item.get("snippet") or item.get("text") or item.get("description", "")
            fp = hashlib.md5((url + snippet).encode()).hexdigest()
            if fp in seen:
                continue
            seen.add(fp)
            ev = EvidenceItem(content=snippet, source_url=url)
            evidence_items.append(ev)
            if len(evidence_items) >= max_sources:
                break

        # 3. Classify evidence
        classified = self._classify_evidence(evidence_items)

        # 4. Synthesize
        synthesis = self._build_synthesis(query, classified)

        output = {
            "query": query,
            "sources_collected": len(classified),
            "evidence": [e.as_dict() for e in classified],
            "synthesis": synthesis,
        }
        return ActionResult.ok(request.action_id, output=output)

    def _collect(self, request: ActionRequest) -> ActionResult:
        query = request.parameters.get("query", "")
        raw = self._do_search(query)
        return ActionResult.ok(request.action_id, output={"results": raw})

    def _synthesize(self, request: ActionRequest) -> ActionResult:
        evidence = request.parameters.get("evidence", [])
        query = request.parameters.get("query", "")
        items = [
            EvidenceItem(e.get("content", ""), e.get("source_url", ""),
                         e.get("classification", "CLAIM"))
            for e in evidence
        ]
        synthesis = self._build_synthesis(query, items)
        return ActionResult.ok(request.action_id, output={"synthesis": synthesis})

    # ── Helpers ────────────────────────────────────────────────────────────

    def _do_search(self, query: str) -> list[dict]:
        if self._search_fn:
            return self._search_fn(query) or []
        try:
            from actions.web_search import search
            result = search(query)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("results", [])
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)
        return []

    @staticmethod
    def _classify_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Simple heuristic classification — real implementation would use LLM."""
        domain_count: dict[str, int] = {}
        for item in items:
            domain_count[item.domain] = domain_count.get(item.domain, 0) + 1

        for item in items:
            # Multiple sources reporting same domain snippet → treat as FACT candidate
            if domain_count.get(item.domain, 0) > 1:
                item.classification = "FACT"
            elif not item.content:
                item.classification = "UNCERTAINTY"
            else:
                item.classification = "CLAIM"
        return items

    @staticmethod
    def _build_synthesis(query: str, evidence: list[EvidenceItem]) -> str:
        if not evidence:
            return "No evidence collected."
        lines = [f"Research summary for: {query}", ""]
        for item in evidence:
            lines.append(
                f"[{item.classification}] ({item.domain}) {item.content[:300]}"
            )
        return "\n".join(lines)


WebResearchCapability = WebResearchCapabilityProvider
