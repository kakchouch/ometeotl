"""Admissibility validator for goal feasibility under perceived capability."""

from __future__ import annotations

from typing import Any, Mapping

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goal_tools import GoalAdmissibilityChecker
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception

from .base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)


class AdmissibilityValidator:
    """Validate admissibility of goals against actor perception constraints."""

    @property
    def name(self) -> str:
        return "admissibility"

    def validate(self, obj: Any, context: ValidationContext) -> ValidationResult:
        goal, actor, perception = self._resolve_inputs(obj, context)
        if goal is None or actor is None or perception is None:
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="ADM-MISSING-CONTEXT",
                        severity=SEVERITY_WARNING,
                        message=(
                            "Admissibility validation requires goal, actor, and "
                            "perception inputs"
                        ),
                    )
                ],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        result = GoalAdmissibilityChecker().check(goal, actor, perception)
        if result.admissible:
            return ValidationResult(
                issues=[],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
                metadata={"reason": result.reason},
            )

        return ValidationResult(
            issues=[
                ValidationIssue(
                    code="ADM-NOT-ADMISSIBLE",
                    severity=SEVERITY_ERROR,
                    message=f"Goal is not admissible: {result.reason}",
                    object_id=goal.id,
                    context={"blocking_constraints": result.blocking_constraints},
                )
            ],
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
        )

    def _resolve_inputs(
        self,
        obj: Any,
        context: ValidationContext,
    ) -> tuple[Goal | None, Actor | None, Perception | None]:
        goal: Goal | None = None
        actor: Actor | None = None
        perception: Perception | None = None

        if isinstance(obj, Goal):
            goal = obj
        if isinstance(obj, Mapping):
            raw_goal = obj.get("goal")
            raw_actor = obj.get("actor")
            raw_perception = obj.get("perception")
            if isinstance(raw_goal, Goal):
                goal = raw_goal
            if isinstance(raw_actor, Actor):
                actor = raw_actor
            if isinstance(raw_perception, Perception):
                perception = raw_perception

        metadata = context.metadata
        if goal is None and isinstance(metadata.get("goal"), Goal):
            goal = metadata.get("goal")
        if actor is None and isinstance(metadata.get("actor"), Actor):
            actor = metadata.get("actor")
        if perception is None and isinstance(metadata.get("perception"), Perception):
            perception = metadata.get("perception")

        return goal, actor, perception
