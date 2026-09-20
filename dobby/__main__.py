from __future__ import annotations

import json
import sys
from pathlib import Path

from computer.diagnostics import collect_environment, format_report, run_live_validation
from memory.commands import handle as memory_command
from brain.defaults import create_registry
from brain.request import BrainRequest
from brain.router import BrainRouter


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "diagnostics"
    if command == "diagnostics":
        print(format_report(collect_environment()))
        return 0
    if command == "validate-linux":
        print(json.dumps(run_live_validation(), indent=2))
        return 0
    if command == "memory" and len(sys.argv) > 2:
        result = memory_command("memory " + " ".join(sys.argv[2:]))
        print(result or "Unknown memory command.")
        return 0 if result else 2
    if command == "context" and len(sys.argv) > 1:
        print(memory_command("context show") or "No context available.")
        return 0
    if command == "brain":
        registry = create_registry()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        if subcommand in {"status", "list"}:
            print(json.dumps({"master_provider": "gemini", "providers": registry.list()}, indent=2))
            return 0
        if subcommand == "usage":
            print(json.dumps({"usage": [], "tracking": "available", "budget_manager": "available"}, indent=2))
            return 0
        if subcommand == "models" and len(sys.argv) > 3:
            from brain.manager import ProviderManager
            print(json.dumps({"provider": sys.argv[3], "models": ProviderManager().list_models(sys.argv[3])}, indent=2))
            return 0
        if subcommand == "test" and len(sys.argv) > 3:
            from brain.manager import ProviderManager
            print(json.dumps(ProviderManager().test_provider(sys.argv[3]), indent=2))
            return 0
        if subcommand == "route" and len(sys.argv) > 3:
            task = " ".join(sys.argv[3:])
            dry_run = "--dry-run" in task
            task = task.replace("--dry-run", "").strip()
            decision = BrainRouter(registry).route(BrainRequest(task=task, role="master"), dry_run=dry_run)
            print(json.dumps(decision, indent=2))
            return 0
        print("Usage: python -m dobby brain status|list|usage|route --dry-run <task>", file=sys.stderr)
        return 2
    if command == "agents":
        from agents.registry import AgentRegistry
        print(json.dumps(AgentRegistry().status(), indent=2))
        return 0
    if command == "acquire":
        from acquisition.manager import AcquisitionManager
        from core.action_loader import discover_actions
        actions = discover_actions(Path(__file__).resolve().parent.parent / "actions", logger=lambda _: None)
        manager = AcquisitionManager(actions)
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        if subcommand == "status":
            print(json.dumps({"discovery": "available", "sandbox": "workspace_only",
                              "candidates": manager.registry.list()}, indent=2)); return 0
        if subcommand == "candidates":
            print(json.dumps(manager.registry.list(), indent=2)); return 0
        if subcommand == "search" and len(sys.argv) > 3:
            print(json.dumps(manager.search(" ".join(sys.argv[3:])), indent=2)); return 0
        if subcommand == "dry-run" and len(sys.argv) > 3:
            print(json.dumps(manager.dry_run(" ".join(sys.argv[3:])), indent=2)); return 0
        if subcommand == "cleanup":
            print(json.dumps(manager.cleanup(), indent=2)); return 0
        print("Usage: python -m dobby acquire status|search <query>|candidates|dry-run <capability>|cleanup", file=sys.stderr)
        return 2
    print("Usage: python -m dobby diagnostics | validate-linux | memory <command> | context", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())