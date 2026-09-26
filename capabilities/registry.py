"""Capability registry — discovers and lists all providers (Phase 19).

Builds and returns a pre-configured CapabilityRouter with all built-in
providers registered.  Each provider self-reports its status.
"""
from __future__ import annotations

from autonomous.capability_router import CapabilityRouter
from capabilities.base import CapabilityStatus
from capabilities.browser import BrowserCapabilityProvider
from capabilities.email import EmailCapabilityProvider
from capabilities.messaging import MessagingCapabilityProvider
from capabilities.phone import PhoneCapabilityProvider
from capabilities.web_research import WebResearchCapabilityProvider


class CapabilityRegistry:
    """Registry of all available Dobby capability providers."""

    def __init__(self):
        self._providers: dict[str, object] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        providers = [
            ("BROWSER", BrowserCapabilityProvider()),
            ("EMAIL", EmailCapabilityProvider()),
            ("MESSAGING", MessagingCapabilityProvider()),
            ("PHONE", PhoneCapabilityProvider()),
            ("WEB_RESEARCH", WebResearchCapabilityProvider()),
            ("WEB", WebResearchCapabilityProvider()),
        ]
        # MCP provider (optional)
        try:
            from mcp.provider import ControlledMCPProvider, MCPRegistry
            mcp_reg = MCPRegistry()
            if mcp_reg._providers:
                class MCPCapabilityProvider:
                    name = "mcp"
                    def status(self) -> str:
                        return CapabilityStatus.AVAILABLE
                    def execute(self, request):
                        from autonomous.action_contract import ActionResult
                        tool = request.parameters.get("tool", "")
                        params = request.parameters.get("tool_parameters", {})
                        provider_name = request.provider or next(iter(mcp_reg._providers))
                        prov = mcp_reg._providers.get(provider_name)
                        if not prov:
                            return ActionResult.fail(request.action_id, f"MCP provider {provider_name!r} not found")
                        result = prov.call_tool(tool, params)
                        from autonomous.action_contract import ActionResult as AR
                        return AR.ok(request.action_id, output=result)
                providers.append(("MCP", MCPCapabilityProvider()))
        except Exception:
            pass

        # Coding agent provider (optional)
        try:
            from development.agent_registry import CodingAgentRegistry
            from development.agent_detector import AgentDetector
            detected = AgentDetector().status()
            if detected.get("detected"):
                class CodingAgentCapabilityProvider:
                    name = "coding_agent"
                    def status(self) -> str:
                        return CapabilityStatus.AVAILABLE
                    def execute(self, request):
                        from autonomous.action_contract import ActionResult
                        from development.agent_supervisor import CodingAgentSupervisor
                        from development.models import CodingTask
                        agent = request.provider or "default"
                        workspace = request.parameters.get("workspace", ".")
                        task = CodingTask(**{k: v for k, v in request.parameters.items()
                                            if k in {"objective", "project_name", "workspace",
                                                      "language", "max_steps"}})
                        result = CodingAgentSupervisor().run_generic(agent, workspace, task)
                        return ActionResult.ok(request.action_id, output=result)
                providers.append(("CODING_AGENT", CodingAgentCapabilityProvider()))
        except Exception:
            pass

        for cap, provider in providers:
            self._providers[cap] = provider

    def build_router(self, confirmation_callback=None) -> CapabilityRouter:
        """Build and return a pre-configured CapabilityRouter."""
        router = CapabilityRouter(confirmation_callback=confirmation_callback)
        for cap, provider in self._providers.items():
            router.register(cap, provider)
        return router

    def status(self) -> list[dict]:
        """Return status of all registered providers."""
        result = []
        for cap, provider in self._providers.items():
            try:
                st = provider.status()
            except Exception:
                st = CapabilityStatus.ERROR
            result.append({
                "capability": cap,
                "provider": getattr(provider, "name", cap.lower()),
                "status": st,
            })
        return result

    def list(self) -> list[str]:
        return list(self._providers.keys())

    def list_capabilities(self) -> list[dict]:
        return self.status()
