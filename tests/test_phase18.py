from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from acquisition.mcp import MCPAcquisition, MCPCandidateStatus
from mcp.models import MCPServerSpec, MCPToolClass


class PhaseEighteenTests(unittest.TestCase):
    def server(self):
        fixture = Path(__file__).parent / "fixtures" / "mcp_test_server.py"
        return MCPServerSpec("phase18", "Phase 18 Test MCP", transport="stdio", command=[sys.executable, str(fixture)], enabled=True, trust_state="TRUSTED", status="CONFIGURED")

    def test_candidate_discovery_inspection_and_protocol(self):
        acquisition = MCPAcquisition()
        candidate = acquisition.discover(self.server())
        self.assertEqual(candidate.status, MCPCandidateStatus.DISCOVERED)
        with tempfile.TemporaryDirectory() as root:
            inspected = acquisition.inspect(candidate, root, {"LICENSE": "MIT License"})
        self.assertEqual(inspected["status"], MCPCandidateStatus.INSPECTED)
        protocol = acquisition.protocol_validate(candidate)
        self.assertTrue(protocol["success"])
        self.assertEqual(candidate.status, MCPCandidateStatus.MCP_PROTOCOL_VALID)
        self.assertGreater(len(candidate.tools), 0)

    def test_unpinned_candidate_requires_review(self):
        acquisition = MCPAcquisition()
        candidate = acquisition.discover(self.server())
        with tempfile.TemporaryDirectory() as root:
            acquisition.inspect(candidate, root, {"LICENSE": "MIT License"})
        acquisition.protocol_validate(candidate)
        result = acquisition.evaluate(candidate)
        self.assertEqual(result["evaluation"]["result"], "REVIEW_REQUIRED")
        self.assertIn("source is not pinned", result["evaluation"]["review_reasons"])
        self.assertFalse(acquisition.approve(candidate)["success"])

    def test_approval_enable_revoke_lifecycle(self):
        acquisition = MCPAcquisition()
        candidate = acquisition.discover(self.server())
        candidate.commit = "abc123"
        candidate.license_info = {"license_detected": True, "license_identifier": "MIT"}
        candidate.tools = [{"name": "get_status", "capability_class": MCPToolClass.READ}]
        acquisition.evaluate(candidate)
        result = acquisition.approve(candidate)
        self.assertTrue(result["success"])
        self.assertTrue(acquisition.enable(candidate)["success"])
        self.assertEqual(acquisition.revoke(candidate)["candidate"]["status"], MCPCandidateStatus.REVOKED)

    def test_network_required_review_and_no_install_side_effect(self):
        acquisition = MCPAcquisition()
        server = self.server()
        server.metadata = {"network_required": True}
        candidate = acquisition.discover(server)
        with tempfile.TemporaryDirectory() as root:
            result = acquisition.inspect(candidate, root, {"LICENSE": "MIT License"})
        self.assertEqual(result["evaluation"]["network"], "REVIEW_REQUIRED")
        self.assertFalse((Path(root) / "installed").exists())


if __name__ == "__main__":
    unittest.main()
