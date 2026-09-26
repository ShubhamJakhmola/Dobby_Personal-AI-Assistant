"""Autonomous Planner — converts a Goal into a validated TaskGraph (Phase 19).

Architecture:
    Goal → AutonomousPlanner → BrainRouter (Gemini)
        → structured plan dict → validate → TaskGraph

Gemini PROPOSES a plan.  Dobby VALIDATES and CONTROLS it.
Gemini is never the execution authority.

Re-planning:
    replan(goal, completed_tasks, observations) is called by the
    AutonomousExecutor when enough steps fail that a fresh plan is
    preferable to continued retry.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from autonomous.goal import Goal, GoalStatus
from autonomous.task_graph import GoalTask, RetryPolicy, TaskGraph

logger = logging.getLogger(__name__)


# ── Structured plan schema ─────────────────────────────────────────────────
#
# Gemini returns a JSON structure matching this schema.
# Dobby validates it before accepting.
#
# plan_steps: list of:
#   {
#     "name": str,
#     "description": str,
#     "dependencies": [str],          # step names (not task_ids)
#     "capability": str,              # capability category
#     "provider": str,
#     "parameters": {…},
#     "expected_result": {…},
#     "verification": {…},
#     "retry_policy": {"max_retries": int, "backoff_seconds": float},
#     "risk_level": str,
#   }

_REQUIRED_STEP_KEYS = {"name", "capability"}
_ALLOWED_CAPABILITIES = {
    "BUILTIN", "OS", "TERMINAL", "FILESYSTEM", "BROWSER", "WEB",
    "EMAIL", "MESSAGING", "PHONE", "CODING_AGENT", "MCP",
    "REMOTE_DEVICE", "DATABASE", "CLOUD", "DOCUMENT", "VISION",
    "LOCAL_AI", "SPECIALIST_AI", "WEB_RESEARCH", "JOB_APPLICATION",
    "CALENDAR",
}


class PlanValidationError(Exception):
    pass


class AutonomousPlanner:
    """Dobby's planning layer.  Uses Gemini for reasoning; owns validation."""

    def __init__(self, brain_router=None):
        self._router = brain_router

    # ── Public interface ───────────────────────────────────────────────────

    def plan(self, goal: Goal, dry_run: bool = False) -> TaskGraph:
        """Generate a TaskGraph for goal.

        Steps:
        1. Ask Gemini for a structured plan.
        2. Validate the plan structure and capabilities.
        3. Build and return a TaskGraph.

        Falls back to a minimal single-step plan if Gemini is unavailable.
        """
        goal.transition(GoalStatus.PLANNING)
        raw_plan = self._ask_gemini(goal)
        steps = self._extract_steps(raw_plan, goal)
        self._validate_steps(steps, goal)
        graph = TaskGraph.from_plan(goal.goal_id, steps)
        goal.plan = steps
        goal.transition(GoalStatus.READY)
        return graph

    def replan(
        self,
        goal: Goal,
        completed_tasks: list[str],
        observations: list[dict],
    ) -> TaskGraph:
        """Generate an updated plan based on partial completion state."""
        goal.transition(GoalStatus.REPLANNING)
        context = {
            "original_goal": goal.original_request,
            "objective": goal.normalized_objective,
            "completed_steps": completed_tasks,
            "observations": observations[-10:],
            "remaining_criteria": goal.success_criteria,
        }
        raw_plan = self._ask_gemini_replan(goal, context)
        steps = self._extract_steps(raw_plan, goal)
        self._validate_steps(steps, goal)
        graph = TaskGraph.from_plan(goal.goal_id, steps)
        goal.plan = steps
        goal.transition(GoalStatus.READY)
        return graph

    # ── Gemini interaction ─────────────────────────────────────────────────

    def _ask_gemini(self, goal: Goal) -> dict:
        """Request a structured plan from the master brain."""
        if not self._router:
            return self._fallback_plan(goal)

        prompt = self._build_planning_prompt(goal)
        try:
            from brain.request import BrainRequest
            request = BrainRequest(
                task=prompt,
                task_type="planning",
                complexity="high",
                required_capabilities=["reasoning", "planning"],
                role="master",
                metadata={"goal_id": goal.goal_id},
            )
            response = self._router.route(request)
            content = response.get("content", "")
            return self._parse_plan_response(content)
        except Exception as exc:
            logger.warning("Gemini planning failed (%s); using fallback plan.", exc)
            return self._fallback_plan(goal)

    def _ask_gemini_replan(self, goal: Goal, context: dict) -> dict:
        """Request a revised plan after partial execution."""
        if not self._router:
            return self._fallback_plan(goal)

        prompt = (
            f"Dobby has been executing a goal but needs to replan.\n\n"
            f"Original goal: {goal.original_request}\n"
            f"Completed steps: {context['completed_steps']}\n"
            f"Recent observations: {json.dumps(context['observations'], indent=2)}\n\n"
            f"Produce a revised structured plan in the same JSON format to "
            f"complete the remaining success criteria: {goal.success_criteria}\n\n"
            f"Return ONLY a JSON object with key 'plan_steps'."
        )
        try:
            from brain.request import BrainRequest
            request = BrainRequest(
                task=prompt,
                task_type="planning",
                complexity="high",
                required_capabilities=["reasoning", "planning"],
                role="master",
                metadata={"goal_id": goal.goal_id, "replanning": True},
            )
            response = self._router.route(request)
            return self._parse_plan_response(response.get("content", ""))
        except Exception as exc:
            logger.warning("Gemini replanning failed (%s); using fallback.", exc)
            return self._fallback_plan(goal)

    # ── Parsing & validation ───────────────────────────────────────────────

    def _parse_plan_response(self, content: str) -> dict:
        """Extract JSON from model response (handles markdown fences)."""
        text = content.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        # Find first { to handle preamble text
        start = text.find("{")
        if start != -1:
            text = text[start:]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _extract_steps(self, raw: dict, goal: Goal) -> list[dict]:
        """Pull plan_steps list from raw dict, or build a fallback."""
        if isinstance(raw, dict) and isinstance(raw.get("plan_steps"), list):
            return raw["plan_steps"]
        # Fallback: single web-research step
        return self._fallback_plan(goal).get("plan_steps", [])

    def _validate_steps(self, steps: list[dict], goal: Goal) -> None:
        """Raise PlanValidationError if the plan violates Dobby policy."""
        if not steps:
            raise PlanValidationError("Planner returned an empty plan.")
        seen_names: set[str] = set()
        for i, step in enumerate(steps):
            missing = _REQUIRED_STEP_KEYS - step.keys()
            if missing:
                raise PlanValidationError(
                    f"Step {i} missing required keys: {missing}"
                )
            name = step.get("name", "")
            if name in seen_names:
                raise PlanValidationError(f"Duplicate step name: {name!r}")
            seen_names.add(name)
            cap = str(step.get("capability", "")).upper()
            if cap and cap not in _ALLOWED_CAPABILITIES:
                raise PlanValidationError(
                    f"Step {name!r} uses unknown capability {cap!r}"
                )
            # Forbidden actions check
            for forbidden in goal.forbidden_actions:
                if forbidden.lower() in str(step).lower():
                    raise PlanValidationError(
                        f"Step {name!r} contains a forbidden action: {forbidden!r}"
                    )

    # ── Fallback ───────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_plan(goal: Goal) -> dict:
        """Minimal plan when Gemini is unavailable."""
        return {
            "plan_steps": [
                {
                    "name": "web_research",
                    "description": f"Research: {goal.normalized_objective or goal.original_request}",
                    "dependencies": [],
                    "capability": "WEB_RESEARCH",
                    "provider": "",
                    "parameters": {"query": goal.normalized_objective or goal.original_request},
                    "expected_result": {"sources_collected": True},
                    "verification": {},
                    "risk_level": "INFORMATIONAL",
                }
            ]
        }

    @staticmethod
    def _build_planning_prompt(goal: Goal) -> str:
        parts = [
            "You are Dobby's planning assistant. Produce a structured execution plan.",
            "",
            f"Goal: {goal.original_request}",
            f"Objective: {goal.normalized_objective}",
        ]
        if goal.constraints:
            parts.append(f"Constraints: {', '.join(goal.constraints)}")
        if goal.success_criteria:
            parts.append(f"Success criteria: {', '.join(goal.success_criteria)}")
        if goal.forbidden_actions:
            parts.append(f"FORBIDDEN actions: {', '.join(goal.forbidden_actions)}")
        parts += [
            "",
            "Return ONLY valid JSON with this structure:",
            '{"plan_steps": [{"name": "str", "description": "str",',
            '  "dependencies": ["step_name"], "capability": "WEB|BROWSER|EMAIL|...",',
            '  "parameters": {}, "expected_result": {}, "risk_level": "INFORMATIONAL"}]}',
            "",
            "Keep steps concrete, bounded, and verifiable. Maximum 20 steps.",
        ]
        return "\n".join(parts)
