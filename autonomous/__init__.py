"""Dobby autonomous general-purpose agent engine (Phase 19).

Architecture:
    USER GOAL → GoalManager → AutonomousPlanner → TaskGraph
             → AutonomousExecutor → CapabilityRouter → providers
             → RecoveryEngine → TaskTimeline → AuditLog
"""
from __future__ import annotations

from autonomous.goal import Goal, GoalStatus
from autonomous.goal_manager import GoalManager

__all__ = ["Goal", "GoalStatus", "GoalManager"]
