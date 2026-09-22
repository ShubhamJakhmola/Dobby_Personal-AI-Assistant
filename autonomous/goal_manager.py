"""GoalManager — top-level autonomous orchestrator (Phase 19).

Accepts natural-language goals, normalizes them, creates TaskGraphs,
runs the autonomous execution loop, and persists state for resumption.

Architecture (Dobby is the authority):
    USER
     ↓
    GoalManager.create_goal()
     ↓
    AutonomousPlanner → Gemini (reasoning only)
     ↓
    TaskGraph (validated by Dobby)
     ↓
    AutonomousExecutor → CapabilityRouter → providers
     ↓
    RecoveryEngine / Replanning
     ↓
    COMPLETED / FAILED
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autonomous.authorization import AuthorizationStore
from autonomous.capability_router import CapabilityRouter
from autonomous.context_builder import ContextBuilder
from autonomous.executor import AutonomousExecutor
from autonomous.goal import Goal, GoalStatus
from autonomous.idempotency import IdempotencyStore
from autonomous.planner import AutonomousPlanner
from autonomous.recovery import RecoveryEngine
from autonomous.task_graph import TaskGraph
from autonomous.timeline import TaskTimeline, TimelineEvent
from security import audit

logger = logging.getLogger(__name__)

_MAX_REPLAN_CYCLES = 3


def _data_dir() -> Path:
    root = Path(os.environ.get("DOBBY_DATA_DIR", Path.home() / ".dobby"))
    root.mkdir(parents=True, exist_ok=True)
    return root


class GoalManager:
    """Manages the full lifecycle of autonomous goals."""

    def __init__(
        self,
        brain_router=None,
        capability_router: CapabilityRouter | None = None,
        memory_manager=None,
        storage_path: Path | None = None,
    ):
        self._brain = brain_router
        self._cap_router = capability_router or CapabilityRouter()
        self._memory = memory_manager
        self._goals: dict[str, Goal] = {}
        self._storage = storage_path or (_data_dir() / "goals.json")
        self._planner = AutonomousPlanner(brain_router)
        self._auth_store = AuthorizationStore()
        self._idem_store = IdempotencyStore()
        self._context_builder = ContextBuilder(memory_manager)
        self._load()

    # ──────────────────────────────────────────────────────────────────────
    # Goal lifecycle
    # ──────────────────────────────────────────────────────────────────────

    def create_goal(
        self,
        natural_language: str,
        *,
        priority: int = 5,
        constraints: list[str] | None = None,
        success_criteria: list[str] | None = None,
        forbidden_actions: list[str] | None = None,
        deadline: str | None = None,
    ) -> Goal:
        """Parse, normalize, and persist a new goal."""
        goal = Goal(
            original_request=natural_language,
            normalized_objective=self._normalize(natural_language),
            priority=priority,
            constraints=constraints or [],
            success_criteria=success_criteria or [],
            forbidden_actions=forbidden_actions or [],
            deadline=deadline,
        )
        goal.transition(GoalStatus.UNDERSTANDING)
        self._goals[goal.goal_id] = goal
        self._save()
        audit.record(event="goal_created", goal_id=goal.goal_id,
                     request=natural_language[:200])
        timeline = TaskTimeline(goal.goal_id)
        timeline.emit(TimelineEvent.GOAL_CREATED, request=natural_language[:200])
        logger.info("Goal created: %s (%s)", goal.goal_id, goal.normalized_objective)
        return goal

    def run_goal(self, goal_id: str, dry_run: bool = False) -> dict:
        """Plan and execute a goal autonomously.

        Handles replanning cycles up to _MAX_REPLAN_CYCLES.
        """
        goal = self._require(goal_id)
        goal.dry_run = dry_run

        executor = AutonomousExecutor(
            capability_router=self._cap_router,
            idempotency_store=self._idem_store,
            recovery_engine=RecoveryEngine(self._cap_router),
            authorization_store=self._auth_store,
        )

        replan_cycles = 0
        completed_tasks: list[str] = []
        observations: list[dict] = []

        while replan_cycles <= _MAX_REPLAN_CYCLES:
            # Plan (or replan)
            try:
                if replan_cycles == 0:
                    graph = self._planner.plan(goal, dry_run=dry_run)
                else:
                    graph = self._planner.replan(goal, completed_tasks, observations)
            except Exception as exc:
                goal.transition(GoalStatus.FAILED)
                self._save()
                return {"success": False, "status": goal.status.value,
                        "error": f"Planning failed: {exc}"}

            # Execute
            result = executor.execute(goal, graph, dry_run=dry_run)
            self._save()

            # Accumulate completed tasks across replan cycles
            completed_tasks.extend(result.get("completed_tasks", []))
            observations.extend(result.get("observations", []))

            if result.get("replan_required"):
                replan_cycles += 1
                logger.info("Replanning cycle %d for goal %s", replan_cycles, goal_id)
                continue

            # Terminal result
            self._save()
            return result

        # Exhausted replan budget
        goal.transition(GoalStatus.FAILED)
        self._save()
        return {
            "success": False,
            "status": goal.status.value,
            "error": "Maximum replanning cycles exceeded.",
        }

    def pause_goal(self, goal_id: str) -> dict:
        goal = self._require(goal_id)
        if goal.status not in {GoalStatus.EXECUTING, GoalStatus.WAITING}:
            return {"success": False, "error": "Goal is not currently running."}
        goal.transition(GoalStatus.WAITING)
        self._save()
        return {"success": True, "goal_id": goal_id, "status": goal.status.value}

    def resume_goal(self, goal_id: str) -> dict:
        goal = self._require(goal_id)
        if goal.status not in {GoalStatus.WAITING, GoalStatus.BLOCKED}:
            return {"success": False, "error": "Goal is not paused."}
        return self.run_goal(goal_id, dry_run=goal.dry_run)

    def cancel_goal(self, goal_id: str) -> dict:
        goal = self._require(goal_id)
        goal.transition(GoalStatus.CANCELLED)
        self._save()
        audit.record(event="goal_cancelled", goal_id=goal_id)
        return {"success": True, "goal_id": goal_id, "status": goal.status.value}

    # ──────────────────────────────────────────────────────────────────────
    # Inspection
    # ──────────────────────────────────────────────────────────────────────

    def inspect_goal(self, goal_id: str) -> dict:
        goal = self._require(goal_id)
        return goal.as_dict()

    def history(self, goal_id: str) -> list[dict]:
        from autonomous.timeline import recent_for_goal
        return recent_for_goal(goal_id, limit=100)

    def list_goals(self) -> list[dict]:
        return [g.summary() for g in sorted(
            self._goals.values(), key=lambda g: g.created_at, reverse=True
        )]

    def status(self, goal_id: str | None = None) -> dict:
        if goal_id:
            goal = self._require(goal_id)
            return goal.summary()
        active = [g for g in self._goals.values()
                  if g.status not in {GoalStatus.COMPLETED, GoalStatus.FAILED,
                                       GoalStatus.CANCELLED}]
        return {
            "total": len(self._goals),
            "active": len(active),
            "active_goals": [g.summary() for g in active],
        }

    # ──────────────────────────────────────────────────────────────────────
    # Authorization pass-through
    # ──────────────────────────────────────────────────────────────────────

    def grant_authorization(self, scope: str, parameters: dict | None = None) -> dict:
        auth = self._auth_store.grant(scope, parameters)
        return auth.as_dict()

    def revoke_authorization(self, auth_id: str) -> dict:
        revoked = self._auth_store.revoke(auth_id)
        return {"success": revoked, "auth_id": auth_id}

    def list_authorizations(self) -> list[dict]:
        return self._auth_store.list()

    # ──────────────────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            self._storage.parent.mkdir(parents=True, exist_ok=True)
            payload = {gid: g.as_dict() for gid, g in self._goals.items()}
            self._storage.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to persist goals: %s", exc)

    def _load(self) -> None:
        if not self._storage.exists():
            return
        try:
            data = json.loads(self._storage.read_text(encoding="utf-8"))
            for gid, raw in data.items():
                self._goals[gid] = Goal.from_dict(raw)
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("Failed to load goals: %s", exc)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _require(self, goal_id: str) -> Goal:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise KeyError(f"Goal not found: {goal_id}")
        return goal

    @staticmethod
    def _normalize(text: str) -> str:
        """Produce a clean objective sentence from raw natural-language input."""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        fillers = ("please ", "could you ", "can you ", "i want you to ",
                   "dobby, ", "hey dobby, ", "dobby ")
        changed = True
        while changed:
            changed = False
            for filler in fillers:
                if text.lower().startswith(filler):
                    text = text[len(filler):].strip()
                    changed = True
        return text[:1].upper() + text[1:] if text else text
