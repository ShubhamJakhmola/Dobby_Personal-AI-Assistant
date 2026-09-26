from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acquisition.dependencies import inspect_dependencies
from acquisition.license import inspect_license
from acquisition.registry import AcquisitionRegistry
from acquisition.security import inspect_security
from mcp.discovery import discover_tools
from mcp.models import MCPServerSpec, MCPToolSpec, MCPTrustState
from mcp.stdio import MCPStdioClient


class MCPCandidateStatus:
    DISCOVERED = "DISCOVERED"
    INSPECTED = "INSPECTED"
    SANDBOXED = "SANDBOXED"
    MCP_PROTOCOL_VALID = "MCP_PROTOCOL_VALID"
    EVALUATED = "EVALUATED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    INSTALLED = "INSTALLED"
    REGISTERED = "REGISTERED"
    ENABLED = "ENABLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
    REMOVED = "REMOVED"


@dataclass
class MCPCandidate:
    candidate_id: str
    server: MCPServerSpec
    version: str = ""
    commit: str = ""
    license_info: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    evaluation: dict[str, Any] = field(default_factory=dict)
    status: str = MCPCandidateStatus.DISCOVERED
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "server": self.server.as_dict(),
            "version": self.version,
            "commit": self.commit,
            "license": self.license_info,
            "dependencies": self.dependencies,
            "tools": self.tools,
            "evaluation": self.evaluation,
            "status": self.status,
            "provenance": self.provenance,
        }


class MCPAcquisition:
    """MCP specialization of Phase 8 acquisition; no automatic install/trust."""
    def __init__(self, acquisition_registry: AcquisitionRegistry | None = None):
        self.registry = acquisition_registry or AcquisitionRegistry()
        self._candidates: dict[str, MCPCandidate] = {}

    def discover(self, server: MCPServerSpec) -> MCPCandidate:
        candidate = MCPCandidate(str(uuid.uuid4()), server, provenance={"source_type": "local_stdio", "pinned": False})
        self._candidates[candidate.candidate_id] = candidate
        return candidate

    def inspect(self, candidate: MCPCandidate, root: str | Path, files: dict[str, str] | None = None) -> dict:
        files = files or {}
        candidate.license_info = inspect_license(files, candidate.server.metadata.get("license", "") if hasattr(candidate.server, "metadata") else "")
        candidate.dependencies = inspect_dependencies(root)
        candidate.evaluation["security"] = inspect_security(files)
        server_metadata = getattr(candidate.server, "metadata", {}) or {}
        candidate.evaluation["network"] = "REVIEW_REQUIRED" if server_metadata.get("network_required") else "DISABLED"
        candidate.status = MCPCandidateStatus.INSPECTED
        if not candidate.commit and not candidate.version:
            candidate.evaluation["provenance"] = "REVIEW_REQUIRED"
        return candidate.as_dict()

    def protocol_validate(self, candidate: MCPCandidate, *, timeout: float = 5.0) -> dict:
        client = MCPStdioClient(candidate.server, timeout=timeout)
        try:
            started = client.start()
            if started.get("status") != "AVAILABLE":
                candidate.status = MCPCandidateStatus.FAILED
                return {"success": False, "status": candidate.status, "error": started.get("error", "MCP initialization failed")}
            tools = client.list_tools()
            candidate.tools = [tool.as_dict() for tool in tools]
            candidate.server.status = "AVAILABLE"
            candidate.status = MCPCandidateStatus.MCP_PROTOCOL_VALID
            candidate.evaluation["protocol"] = {"initialize": "PASS", "tools_list": "PASS", "tool_count": len(tools)}
            return {"success": True, "status": candidate.status, "tools": candidate.tools}
        except Exception as exc:
            candidate.status = MCPCandidateStatus.FAILED
            candidate.evaluation["protocol"] = {"initialize": "FAIL", "error": str(exc)}
            return {"success": False, "status": candidate.status, "error": str(exc)}
        finally:
            client.shutdown()

    def evaluate(self, candidate: MCPCandidate) -> dict:
        review = []
        if not candidate.commit and not candidate.version:
            review.append("source is not pinned")
        if not candidate.license_info.get("license_detected"):
            review.append("license unknown")
        if candidate.evaluation.get("network") == "REVIEW_REQUIRED":
            review.append("network required")
        if any(tool.get("capability_class") == "UNKNOWN" for tool in candidate.tools):
            review.append("unknown tool classification")
        candidate.evaluation["result"] = "REVIEW_REQUIRED" if review else "PASS"
        candidate.evaluation["review_reasons"] = review
        candidate.status = MCPCandidateStatus.APPROVAL_REQUIRED
        return candidate.as_dict()

    def approve(self, candidate: MCPCandidate) -> dict:
        if candidate.status != MCPCandidateStatus.APPROVAL_REQUIRED or candidate.evaluation.get("result") != "PASS":
            return {"success": False, "status": candidate.status, "error": "candidate requires successful evaluation and explicit approval"}
        candidate.status = MCPCandidateStatus.APPROVED
        candidate.server.trust_state = MCPTrustState.TRUSTED
        return {"success": True, "candidate": candidate.as_dict()}

    def enable(self, candidate: MCPCandidate) -> dict:
        if candidate.status != MCPCandidateStatus.APPROVED:
            return {"success": False, "status": candidate.status, "error": "candidate must be approved first"}
        candidate.server.enabled = True
        candidate.status = MCPCandidateStatus.ENABLED
        return {"success": True, "candidate": candidate.as_dict()}

    def revoke(self, candidate: MCPCandidate) -> dict:
        candidate.server.enabled = False
        candidate.server.trust_state = MCPTrustState.REVOKED
        candidate.status = MCPCandidateStatus.REVOKED
        return {"success": True, "candidate": candidate.as_dict()}
