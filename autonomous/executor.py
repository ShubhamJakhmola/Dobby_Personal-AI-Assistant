"""AutonomousExecutor — the core autonomous execution loop (Phase 19).

Executes a TaskGraph step-by-step:
  for each GoalTask (topological order):
    → CapabilityRouter.route(ActionRequest)
    → observe result
    → verify
    → on failure: RecoveryEngine
    → on replan signal: pause and request replanning
    → record to TaskTimeline + AuditLog

Key design:
- Dobby is the execution authority.  The CapabilityRouter routes; providers execute.
- Gemini never executes directly.
- IdempotencyStore is checked before every external action.
- AuthorizationStore is checked for scoped autonomous actions.
- Dry-run mode: no external effects; produces a full execution plan.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from autonomous.action_contract import ActionRequest, ActionResult, ActionStatus, RiskLevel
from autonomous.authorization import AuthorizationStore
from autonomous.capability_router import CapabilityRouter
from autonomous.goal import Goal, GoalStatus
from autonomous.idempotency import IdempotencyStore
from autonomous.recovery import RecoveryEngine, RecoveryStrategy
from autonomous.risk import classify_action, requires_confirmation
from autonomous.task_graph import GoalTask, GoalTaskStatus, TaskGraph
from autonomous.timeline import TaskTimeline, TimelineEvent
from capabilities.base import CapabilityStatus
from security import audit

logger = logging.getLogger(__name__)


class AutonomousExecutor:
    """Executes a TaskGraph on behalf of a Goal."""

    def __init__(
        self,
        capability_router: CapabilityRouter | None = None,
        idempotency_store: IdempotencyStore | None = None,
        recovery_engine: RecoveryEngine | None = None,
        confirmation_callback: Callable | None = None,
        authorization_store=None,
    ):
        self._router = capability_router or CapabilityRouter()
        self._idem = idempotency_store or IdempotencyStore()
        self._recovery = recovery_engine or RecoveryEngine(self._router, confirmation_callback)
        self._confirm = confirmation_callback
        self._auth = authorization_store or AuthorizationStore()

    # ── Public interface ───────────────────────────────────────────────────

    def execute(self, goal: Goal, graph: TaskGraph, dry_run: bool = False) -> dict:
        """Execute every task in topological order.

        Returns a summary dict with success flag and per-task results.
        """
        timeline = TaskTimeline(goal.goal_id)
        timeline.emit(TimelineEvent.PLAN_CREATED, steps=len(graph.all_tasks()))

        try:
            ordered = graph.topological_order()
        except ValueError as exc:
            return self._fail_result(goal, str(exc), timeline)

        goal.transition(GoalStatus.EXECUTING)
        completed: set[str] = set()
        failed: set[str] = set()
        all_results: list[dict] = []
        need_replan = False

        for task in ordered:
            if goal.status == GoalStatus.CANCELLED:
                break

            # Skip if any dependency failed
            if any(dep in failed for dep in task.dependencies):
                graph.mark_failed(task.task_id, "dependency failed")
                failed.add(task.task_id)
                continue

            timeline.emit(TimelineEvent.STEP_STARTED, task_id=task.task_id, name=task.name)
            graph.mark_running(task.task_id)

            result, need_replan = self._execute_task(task, goal, dry_run, timeline)
            all_results.append(result.as_dict())

            if need_replan:
                goal.transition(GoalStatus.REPLANNING)
                return {
                    "success": False,
                    "status": GoalStatus.REPLANNING.value,
                    "replan_required": True,
                    "results": all_results,
                    "completed_tasks": list(completed),
                    "observations": [r for r in all_results if not r.get("success")],
                }

            if result.success or result.status in {ActionStatus.IDEMPOTENT_SKIP, ActionStatus.SKIPPED_DRY_RUN}:
                graph.mark_completed(task.task_id, result.as_dict())
                completed.add(task.task_id)
                timeline.emit(TimelineEvent.VERIFIED, task_id=task.task_id)
            else:
                graph.mark_failed(task.task_id, result.error)
                failed.add(task.task_id)

        overall_success = graph.is_complete() and not graph.has_failures()
        if overall_success:
            goal.transition(GoalStatus.COMPLETED)
            timeline.emit(TimelineEvent.GOAL_COMPLETED)
        elif goal.status not in {GoalStatus.CANCELLED, GoalStatus.WAITING, GoalStatus.REPLANNING}:
            goal.transition(GoalStatus.FAILED)
            timeline.emit(TimelineEvent.GOAL_FAILED)

        return {
            "success": overall_success,
            "status": goal.status.value,
            "results": all_results,
            "completed_tasks": list(completed),
            "observations": [r for r in all_results if not r.get("success")],
            "graph_summary": graph.summary(),
            "dry_run": dry_run,
        }

    # ── Task execution ─────────────────────────────────────────────────────

    def _execute_task(
        self,
        task: GoalTask,
        goal: Goal,
        dry_run: bool,
        timeline: TaskTimeline,
    ) -> tuple[ActionResult, bool]:
        """Execute a single GoalTask with idempotency, retry, and recovery.

        Returns (ActionResult, need_replan).
        """
        # Build ActionRequest
        idempotency_key = self._make_idempotency_key(task, goal)
        risk = classify_action(task.capability, task.parameters.get("action", ""), task.parameters)

        request = ActionRequest(
            goal_id=goal.goal_id,
            task_id=task.task_id,
            capability=task.capability,
            provider=task.provider,
            parameters=task.parameters,
            idempotency_key=idempotency_key,
            risk_level=risk,
            dry_run=dry_run,
        )

        # ── Confirmation gate check ───────────────────────────────────────
        prov_obj = self._router.get_provider(task.capability)
        prov_status = prov_obj.status() if prov_obj and hasattr(prov_obj, "status") else ""
        if (requires_confirmation(risk) or prov_status == CapabilityStatus.REQUIRES_CONFIRMATION) and not self._auth.is_authorized(task.capability, task.parameters):
            goal.transition(GoalStatus.WAITING)
            timeline.emit(TimelineEvent.CONFIRMATION_REQUIRED, task_id=task.task_id, risk=risk.value)
            return (
                ActionResult(
                    action_id=request.action_id,
                    status=ActionStatus.REQUIRES_CONFIRMATION,
                    error=f"Task '{task.task_id}' requires confirmation (risk={risk.value}).",
                ),
                False,
            )

        # ── Idempotency check ──────────────────────────────────────────────
        if idempotency_key and not dry_run:
            existing = self._idem.check(idempotency_key)
            if existing:
                logger.info("Idempotency hit for task %s", task.task_id)
                return (
                    ActionResult.idempotent(
                        request.action_id,
                        existing.get("external_reference", ""),
                        existing.get("result"),
                    ),
                    False,
                )

        timeline.emit(
            TimelineEvent.CAPABILITY_SELECTED,
            task_id=task.task_id,
            capability=task.capability,
            risk=risk.value,
        )

        # ── Execute with retry/recovery ────────────────────────────────────
        result = self._router.route(request)
        task.attempts += 1

        timeline.emit(
            TimelineEvent.ACTION_EXECUTED,
            task_id=task.task_id,
            status=result.status.value,
            error=result.error or None,
        )

        # ── Recovery loop ──────────────────────────────────────────────────
        need_replan = False
        while not result.success and result.status not in {
            ActionStatus.SKIPPED_DRY_RUN,
            ActionStatus.IDEMPOTENT_SKIP,
            ActionStatus.REQUIRES_CONFIRMATION,
        }:
            strategy, meta = self._recovery.recover(task, result, task.attempts)
            timeline.emit(
                TimelineEvent.RECOVERY_STRATEGY,
                task_id=task.task_id,
                strategy=strategy.value,
                **{k: v for k, v in meta.items() if k not in {"task", "strategy"}},
            )

            if strategy == RecoveryStrategy.ABORT:
                break
            if strategy == RecoveryStrategy.REPLAN:
                need_replan = True
                break
            if strategy == RecoveryStrategy.ASK_USER:
                goal.transition(GoalStatus.WAITING)
                timeline.emit(TimelineEvent.WAITING, task_id=task.task_id, reason=result.error)
                break

            # Retry with same or alternative capability
            if strategy == RecoveryStrategy.ALTERNATIVE_CAPABILITY:
                alt = meta.get("alternative_capability", "")
                if alt:
                    request.capability = alt
                    task.capability = alt
                    timeline.emit(TimelineEvent.RETRY, task_id=task.task_id, alt_capability=alt)

            task.attempts += 1
            result = self._router.route(request)
            timeline.emit(
                TimelineEvent.ACTION_EXECUTED,
                task_id=task.task_id,
                status=result.status.value,
                attempt=task.attempts,
            )

        # ── Persist external action to idempotency store ───────────────────
        if result.success and idempotency_key and not dry_run:
            if requires_confirmation(risk) or risk in {
                RiskLevel.IRREVERSIBLE_EXTERNAL,
                RiskLevel.REVERSIBLE_EXTERNAL,
            }:
                self._idem.record(
                    idempotency_key,
                    action=f"{task.capability}.{task.parameters.get('action', '')}",
                    target=str(task.parameters.get("target", task.name)),
                    result=result.output,
                    external_reference=result.external_reference,
                )

        # ── Audit every action ─────────────────────────────────────────────
        audit.record(
            event="autonomous_action",
            goal_id=goal.goal_id,
            task_id=task.task_id,
            capability=task.capability,
            action=task.parameters.get("action", ""),
            status=result.status.value,
            risk=risk.value,
            dry_run=dry_run,
        )

        timeline.emit(TimelineEvent.RESULT_RECEIVED, task_id=task.task_id, success=result.success)
        return result, need_replan

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _make_idempotency_key(task: GoalTask, goal: Goal) -> str:
        """Create a deterministic idempotency key for external tasks."""
        risk = classify_action(
            task.capability,
            task.parameters.get("action", ""),
            task.parameters,
        )
        if risk in {RiskLevel.IRREVERSIBLE_EXTERNAL, RiskLevel.REVERSIBLE_EXTERNAL}:
            target = str(task.parameters.get("target", task.name))
            return f"{goal.goal_id}:{task.name}:{task.capability}:{target}"
        return ""

    @staticmethod
    def _fail_result(goal: Goal, error: str, timeline: TaskTimeline) -> dict:
        goal.transition(GoalStatus.FAILED)
        timeline.emit(TimelineEvent.GOAL_FAILED, error=error)
        return {"success": False, "status": goal.status.value, "error": error, "results": []}
