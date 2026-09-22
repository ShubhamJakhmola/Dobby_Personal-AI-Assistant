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
    if command == "mcp":
        from mcp.provider import MCPRegistry, ControlledMCPProvider
        registry = MCPRegistry()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        if subcommand in {"status", "list"}:
            providers = []
            for name, provider in registry._providers.items():
                providers.append({"name": name, "capabilities": provider.capabilities()})
            print(json.dumps({"enabled": bool(providers), "providers": providers}, indent=2)); return 0
        if subcommand == "register" and len(sys.argv) > 3:
            name = sys.argv[3]
            registry.register(ControlledMCPProvider(name, {}))
            print(json.dumps({"registered": True, "provider": name, "capabilities": []}, indent=2)); return 0
        print("Usage: python -m dobby mcp status|list|register <provider>", file=sys.stderr); return 2
    if command == "agents":
        from agents.registry import AgentRegistry
        print(json.dumps(AgentRegistry().status(), indent=2))
        return 0
    if command == "device":
        from remote.device_registry import DeviceRegistry
        registry = DeviceRegistry()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        if subcommand == "status":
            print(json.dumps({"enabled": True, "transport": "in-memory", "secure_mode": "development", "devices": registry.status()}, indent=2)); return 0
        if subcommand == "list":
            print(json.dumps(registry.list(), indent=2)); return 0
        if subcommand == "discover":
            print(json.dumps({"status": "not_run", "reason": "phase 11 uses explicit enrollment for local test devices"}, indent=2)); return 0
        if subcommand == "enroll":
            print(json.dumps({"status": "ENROLLING", "reason": "explicit device enrollment required"}, indent=2)); return 0
        print("Usage: python -m dobby device status|list|discover|enroll", file=sys.stderr); return 2
    if command == "remote":
        from remote.device_registry import DeviceRegistry
        registry = DeviceRegistry()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        if subcommand == "status":
            print(json.dumps({"enabled": True, "transport": "in-memory", "secure_mode": "development", "connected_devices": registry.status()}, indent=2)); return 0
        if subcommand == "connections":
            print(json.dumps({"connections": registry.status()}, indent=2)); return 0
        if subcommand == "security":
            print(json.dumps({"secure_mode": "development", "tls": "development_insecure", "credential_storage": "not_verified"}, indent=2)); return 0
        if subcommand == "server":
            from remote.server import DobbyCoreServer
            host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
            port = int(sys.argv[4]) if len(sys.argv) > 4 else 8765
            server = DobbyCoreServer(host=host, port=port, secure_mode="development")
            print(json.dumps({"status": "starting", "host": host, "port": port, "secure_mode": "development"}, indent=2));
            server.serve_forever(); return 0
        print("Usage: python -m dobby remote status|connections|security|server [host] [port]", file=sys.stderr); return 2
    if command == "coding":
        from development.agent_detector import AgentDetector
        from development.agent_registry import CodingAgentRegistry
        from development.project_manager import ProjectManager
        registry = CodingAgentRegistry()
        projects = ProjectManager()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        if subcommand in {"status", "list", "detect"}:
            data = AgentDetector().status() if subcommand in {"status", "detect"} else {"agents": registry.list()}
            print(json.dumps(data, indent=2))
            return 0
        if subcommand == "test" and len(sys.argv) > 3:
            agent = registry.get(sys.argv[3])
            if not agent:
                print(json.dumps({"success": False, "status": "NOT_FOUND", "agent": sys.argv[3]}, indent=2))
                return 1
            print(json.dumps({"success": bool(agent.get("available")), "status": agent.get("status"),
                              "agent": agent, "note": "no prompts were executed"}, indent=2))
            return 0 if agent.get("available") else 1
        if subcommand == "workspace" and len(sys.argv) > 3:
            action = sys.argv[3]
            if action == "list":
                print(json.dumps(projects.status(), indent=2)); return 0
            if action == "create" and len(sys.argv) > 4:
                print(json.dumps(projects.create_project(sys.argv[4]), indent=2)); return 0
            if action == "status" and len(sys.argv) > 4:
                workspace = projects.locate_project(sys.argv[4])
                if not workspace:
                    print(json.dumps({"found": False, "name": sys.argv[4]}, indent=2)); return 1
                print(json.dumps({"found": True, "workspace": workspace,
                                  "state": projects.read_project_state(workspace["path"])}, indent=2)); return 0
        print("Usage: python -m dobby coding status|list|detect|test <agent>|workspace list|create <name>|status <name>", file=sys.stderr)
        return 2
    if command == "build":
        from development.build.workflow import BuildWorkflow
        from development.workspace import WorkspaceManager
        workflow = BuildWorkflow()
        manager = WorkspaceManager()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        dry_run = "--dry-run" in sys.argv
        args = [item for item in sys.argv[3:] if item != "--dry-run"]
        if subcommand == "status":
            print(json.dumps({"enabled": True, "workflows": len(manager.list_projects()),
                              "active_workflows": 0, "repair_limit_default": 3,
                              "workspace": manager.status()}, indent=2))
            return 0
        if subcommand == "list":
            print(json.dumps({"projects": manager.list_projects()}, indent=2)); return 0
        if subcommand == "create" and args:
            workspace = manager.create_project(args[0])
            print(json.dumps(workspace.as_dict(), indent=2)); return 0
        if subcommand == "run" and args:
            project = args[0]
            objective = " ".join(args[1:]).strip() or f"Build project {project}"
            print(json.dumps(workflow.run(project, objective, dry_run=dry_run), indent=2))
            return 0
        if subcommand == "inspect" and args:
            print(json.dumps(workflow.inspect(args[0]), indent=2)); return 0
        if subcommand == "verify" and args:
            print(json.dumps(workflow.verify(args[0]), indent=2)); return 0
        if subcommand == "cancel" and args:
            print(json.dumps(workflow.cancel(args[0]), indent=2)); return 0
        if subcommand == "history" and args:
            print(json.dumps(workflow.history(args[0]), indent=2)); return 0
        if subcommand == "resume" and args:
            print(json.dumps(workflow.resume(args[0]), indent=2)); return 0
        print("Usage: python -m dobby build status|list|create <project>|run <project> [objective] [--dry-run]|inspect|verify|cancel|history|resume <project>", file=sys.stderr)
        return 2
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
    if command == "goal":
        from autonomous.goal_manager import GoalManager
        manager = GoalManager()
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "status"
        dry_run = "--dry-run" in sys.argv
        args = [a for a in sys.argv[3:] if a != "--dry-run"]
        if subcommand == "status":
            goal_id = args[0] if args else None
            print(json.dumps(manager.status(goal_id), indent=2)); return 0
        if subcommand == "list":
            print(json.dumps({"goals": manager.list_goals()}, indent=2)); return 0
        if subcommand == "create" and args:
            goal = manager.create_goal(" ".join(args))
            print(json.dumps(goal.as_dict(), indent=2)); return 0
        if subcommand == "run" and args:
            raw = " ".join(args)
            try:
                goal = manager.create_goal(raw)
                target_id = goal.goal_id
            except Exception:
                target_id = raw
            res = manager.run_goal(target_id, dry_run=dry_run)
            print(json.dumps(res, indent=2)); return 0
        if subcommand == "pause" and args:
            print(json.dumps(manager.pause_goal(args[0]), indent=2)); return 0
        if subcommand == "resume" and args:
            print(json.dumps(manager.resume_goal(args[0]), indent=2)); return 0
        if subcommand == "cancel" and args:
            print(json.dumps(manager.cancel_goal(args[0]), indent=2)); return 0
        if subcommand == "inspect" and args:
            print(json.dumps(manager.inspect_goal(args[0]), indent=2)); return 0
        if subcommand == "history" and args:
            print(json.dumps({"history": manager.history(args[0])}, indent=2)); return 0
        print("Usage: python -m dobby goal status [id]|list|create <req>|run <req|id> [--dry-run]|pause|resume|cancel|inspect|history <id>", file=sys.stderr)
        return 2
    print("Usage: python -m dobby diagnostics | validate-linux | memory <command> | context", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
