"""Goal feasibility and admissibility tools.

This module provides model-level helpers for second-order teleology checks:
- feasibility: whether a projected perception satisfies a goal target condition;
- admissibility: whether a goal is actor-consistent and within perceived limits.

The logic remains domain-agnostic and teleologically neutral: concrete goals,
values, and semantics are still defined by the domain model.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

from .actors import Actor
from .base import JsonMap, ObjectId, _canonical_json_map
from .goals import Goal
from .perception import Perception
from .projection import ProjectedPerceptionState


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def _condition_value_matches(expected: Any, actual: Any) -> bool:
    """Return True when expected condition is satisfied by the actual value.

    Matching rules are intentionally minimal and deterministic:
    - scalar values must match exactly;
    - list values must match exactly (ordered equality);
    - mapping values are treated as subset constraints recursively.
    """
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return False
        for key, expected_value in expected.items():
            if key not in actual:
                return False
            if not _condition_value_matches(expected_value, actual[key]):
                return False
        return True
    return bool(expected == actual)


def _projected_condition_view(
    projected: ProjectedPerceptionState,
) -> JsonMap:
    """Build the condition view used for goal feasibility matching."""
    view = dict(projected.perception.context)
    view.setdefault("perception_id", projected.perception.id)
    view.setdefault("actor_id", projected.perception.actor_id)
    view.setdefault("source_id", projected.perception.source_id)
    view.setdefault("source_perception_id", projected.source_perception_id)
    view.setdefault("generating_action_id", projected.generating_action_id)
    return _canonical_json_map(view)


@dataclass
class GoalFeasibilityResult:
    """Result of evaluating whether a projected state can satisfy a goal."""

    reachable: bool
    confidence: float
    matching_keys: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.confidence = float(self.confidence)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("GoalFeasibilityResult confidence must be in [0, 1]")

    def to_dict(self) -> JsonMap:
        return {
            "reachable": bool(self.reachable),
            "confidence": float(self.confidence),
            "matching_keys": sorted(self.matching_keys),
            "metadata": _canonical_json_map(self.metadata),
        }


class GoalFeasibilityTool(ABC):
    """Abstract feasibility evaluator between Goal and ProjectedPerceptionState."""

    @abstractmethod
    def evaluate(
        self,
        goal: Goal,
        projected: ProjectedPerceptionState,
    ) -> GoalFeasibilityResult:
        """Evaluate whether a projected perception can satisfy a goal."""


class DefaultGoalFeasibilityTool(GoalFeasibilityTool):
    """Default condition-key matching feasibility evaluator."""

    def evaluate(
        self,
        goal: Goal,
        projected: ProjectedPerceptionState,
    ) -> GoalFeasibilityResult:
        target_condition = dict(goal.target_condition)
        if not target_condition:
            return GoalFeasibilityResult(
                reachable=False,
                confidence=0.0,
                matching_keys=[],
                metadata={
                    "reason": "empty_target_condition",
                    "condition_keys": [],
                },
            )

        if (
            goal.target_perception_id is not None
            and goal.target_perception_id != projected.perception.id
        ):
            return GoalFeasibilityResult(
                reachable=False,
                confidence=0.0,
                matching_keys=[],
                metadata={
                    "reason": "target_perception_id_mismatch",
                    "expected_target_perception_id": goal.target_perception_id,
                    "projected_perception_id": projected.perception.id,
                },
            )

        projected_view = _projected_condition_view(projected)
        matched_keys: list[str] = []
        for key, expected_value in target_condition.items():
            if key not in projected_view:
                continue
            if _condition_value_matches(expected_value, projected_view[key]):
                matched_keys.append(str(key))

        total = len(target_condition)
        matched = len(matched_keys)
        confidence = float(matched) / float(total)
        return GoalFeasibilityResult(
            reachable=(matched == total and total > 0),
            confidence=confidence,
            matching_keys=sorted(matched_keys),
            metadata={
                "condition_keys": sorted(str(key) for key in target_condition.keys()),
                "matched_count": matched,
                "total_count": total,
            },
        )


@dataclass
class GoalAdmissibilityResult:
    """Result of evaluating whether a goal is admissible for an actor."""

    admissible: bool
    reason: str = ""
    blocking_constraints: list[ObjectId] = field(default_factory=list)

    def to_dict(self) -> JsonMap:
        return {
            "admissible": bool(self.admissible),
            "reason": self.reason,
            "blocking_constraints": sorted(
                str(cid) for cid in self.blocking_constraints
            ),
        }


class GoalAdmissibilityChecker:
    """Minimal F-13 admissibility checker grounded in actor perception.

    Checks:
    - goal.actor_id must match the actor under evaluation;
    - goal must be linked to actor through actor.relations['goal'];
    - blocking constraints from perception context can invalidate admissibility;
    - horizon max_steps must be achievable with perceived projection capacity.
    """

    def check(
        self,
        goal: Goal,
        actor: Actor,
        perception: Perception,
    ) -> GoalAdmissibilityResult:
        if goal.actor_id != actor.id:
            return GoalAdmissibilityResult(
                admissible=False,
                reason="goal_actor_mismatch",
            )

        actor_goal_ids = set(str(gid) for gid in actor.relations.get("goal", []))
        if goal.id not in actor_goal_ids:
            return GoalAdmissibilityResult(
                admissible=False,
                reason="goal_not_linked_to_actor",
            )

        actor_constraint_ids = set(
            str(constraint_id)
            for constraint_id in actor.relations.get("constraint", [])
        )
        blocked_constraints = set(
            _as_string_list(perception.context.get("blocked_constraints"))
        )
        blocking = sorted(actor_constraint_ids.intersection(blocked_constraints))
        if blocking:
            return GoalAdmissibilityResult(
                admissible=False,
                reason="blocked_by_constraints",
                blocking_constraints=blocking,
            )

        max_steps_value = goal.horizon.get("max_steps")
        if max_steps_value is not None:
            try:
                max_steps = int(max_steps_value)
            except (TypeError, ValueError):
                return GoalAdmissibilityResult(
                    admissible=False,
                    reason="invalid_goal_horizon_max_steps",
                )
            available = perception.context.get("available_projection_steps")
            if available is not None:
                try:
                    available_steps = int(available)
                except (TypeError, ValueError):
                    return GoalAdmissibilityResult(
                        admissible=False,
                        reason="invalid_perceived_projection_capacity",
                    )
                if available_steps < max_steps:
                    return GoalAdmissibilityResult(
                        admissible=False,
                        reason="insufficient_projection_capacity",
                    )

        return GoalAdmissibilityResult(
            admissible=True,
            reason="admissible",
        )
