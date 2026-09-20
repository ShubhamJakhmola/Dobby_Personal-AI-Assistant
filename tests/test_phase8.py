import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import Mock

from acquisition.dependencies import inspect_dependencies
from acquisition.discovery import CapabilityGapAnalyzer, candidate_from_github
from acquisition.evaluators import evaluate_candidate
from acquisition.github import GitHubClient
from acquisition.lifecycle import approve, reject
from acquisition.license import inspect_license
from acquisition.manager import AcquisitionManager
from acquisition.models import CandidateRepository, CandidateStatus
from acquisition.registry import AcquisitionRegistry
from acquisition.sandbox import Sandbox
from acquisition.security import inspect_security


class PhaseEightTests(unittest.TestCase):
    def test_existing_capability_prevents_gap(self):
        registry = Mock(); registry.names.return_value = {"terminal_execute"}
        result = CapabilityGapAnalyzer(registry).analyze("terminal.execute")
        self.assertFalse(result["missing"])

    def test_capability_request_created_for_gap(self):
        registry = Mock(); registry.names.return_value = set()
        result = CapabilityGapAnalyzer(registry).analyze("pdf_tables", "extract PDF tables", ["read_pdf"])
        self.assertTrue(result["missing"])
        self.assertEqual(result["request"]["name"], "pdf_tables")

    def test_github_metadata_parsing(self):
        candidate = candidate_from_github({"id": 1, "name": "tool", "html_url": "https://github.com/a/tool",
                                           "owner": {"login": "a"}, "license": {"spdx_id": "MIT"}, "stargazers_count": 4})
        self.assertEqual(candidate.owner, "a"); self.assertEqual(candidate.license, "MIT")

    def test_github_unavailable_is_structured(self):
        session = Mock(); session.get.side_effect = Exception("offline")
        result = GitHubClient(session).search("pdf")
        self.assertFalse(result["success"])

    def test_license_dependency_security_inspection(self):
        license_result = inspect_license({"LICENSE": "MIT License\nPermission is hereby granted"})
        self.assertEqual(license_result["license_identifier"], "MIT")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); (path / "requirements.txt").write_text("requests\n", encoding="utf-8")
            self.assertIn("requests", inspect_dependencies(path)["dependencies"])
        security = inspect_security({"setup.sh": "sudo rm -rf /tmp/x"})
        self.assertEqual(security["status"], "REVIEW_REQUIRED")

    def test_sandbox_minimal_environment_and_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Sandbox(Path(directory)).run([sys.executable, "-c", "print('ok')"], Path(directory), network=False)
        self.assertTrue(result["success"]); self.assertEqual(result["network"], "disabled")

    def test_evaluation_is_factual_not_a_score(self):
        candidate = CandidateRepository("c", "tool", license="MIT")
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_candidate(candidate, {"LICENSE": "MIT License"}, directory)
        self.assertIn("license", result); self.assertNotIn("score", result)

    def test_lifecycle_reject_and_approve_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = AcquisitionRegistry(directory)
            candidate = CandidateRepository("c", "tool")
            registry.save(candidate)
            self.assertFalse(approve(candidate, registry)["success"])
            registry.transition(candidate, CandidateStatus.INSPECTING)
            registry.transition(candidate, CandidateStatus.SANDBOXED)
            registry.transition(candidate, CandidateStatus.TESTING)
            self.assertTrue(approve(candidate, registry)["success"])
            self.assertEqual(reject(candidate, registry)["success"], True)

    def test_failed_candidate_cannot_register(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = CandidateRepository("c", "tool")
            manager = AcquisitionManager(Mock(), registry=AcquisitionRegistry(directory))
            result = manager.register_adapter(candidate, "demo")
        self.assertFalse(result["success"]); self.assertEqual(result["error_category"], "approval_required")

    def test_dry_run_has_no_side_effects(self):
        registry = Mock(); registry.names.return_value = set()
        github = Mock(); github.search.return_value = {"success": True, "candidates": []}
        with tempfile.TemporaryDirectory() as directory:
            manager = AcquisitionManager(registry, github=github, registry=AcquisitionRegistry(directory), sandbox=Sandbox(Path(directory) / "sandbox"))
            result = manager.dry_run("missing", "missing capability")
            self.assertTrue(result["dry_run"]); self.assertEqual(result["side_effects"], [])
            self.assertFalse((Path(directory) / "sandbox").exists())

    def test_no_secrets_in_candidate_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Sandbox(Path(directory)); workspace = sandbox.workspace("safe")
            result = sandbox.run([sys.executable, "-c", "import os; print('GEMINI_API_KEY' in os.environ)"], workspace)
            self.assertIn("False", result["stdout"])


if __name__ == "__main__":
    unittest.main()