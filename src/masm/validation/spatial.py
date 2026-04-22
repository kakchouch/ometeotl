"""Spatial validator enforcing shared-space interaction constraints."""

from __future__ import annotations

from typing import Any, Mapping

from masm.model.actions import Action
from masm.model.world import World

from .base import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)


class SpatialValidator:
    """Validate actor and interaction references against world space membership."""

    @property
    def name(self) -> str:
        return "spatial"

    def validate(self, obj: Any, context: ValidationContext) -> ValidationResult:
        world = context.metadata.get("world")
        if not isinstance(world, World):
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="SPATIAL-NO-WORLD",
                        severity=SEVERITY_WARNING,
                        message="Spatial validation requires a World in context metadata",
                    )
                ],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        actor_id = ""
        space_id = ""
        if isinstance(obj, Action):
            actor_id = obj.actor_id
            space_id = obj.space_id
        elif isinstance(obj, Mapping):
            actor_id = str(obj.get("actor_id") or "")
            space_id = str(obj.get("space_id") or "")

        issues: list[ValidationIssue] = []

        if not space_id:
            return ValidationResult(
                issues=[],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        if world.get_space(space_id) is None:
            issues.append(
                ValidationIssue(
                    code="SPATIAL-UNKNOWN-SPACE",
                    severity=SEVERITY_ERROR,
                    message=f"Referenced space '{space_id}' does not exist in world",
                    object_id=actor_id,
                )
            )
            return ValidationResult(
                issues=issues,
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        if actor_id:
            objects_in_space = world.space_object_graph.list_objects_in_space(space_id)
            if actor_id not in objects_in_space:
                issues.append(
                    ValidationIssue(
                        code="SPATIAL-ACTOR-NOT-IN-SPACE",
                        severity=SEVERITY_ERROR,
                        message=(
                            f"Actor '{actor_id}' is not present in space '{space_id}'"
                        ),
                        object_id=actor_id,
                    )
                )

        target_actor_id = str(context.metadata.get("target_actor_id") or "")
        if target_actor_id:
            shared = world.space_object_graph.shared_spaces_ids_for_objects(
                actor_id,
                target_actor_id,
            )
            if not shared:
                issues.append(
                    ValidationIssue(
                        code="SPATIAL-NO-SHARED-SPACE",
                        severity=SEVERITY_ERROR,
                        message=(
                            f"Actors '{actor_id}' and '{target_actor_id}' do not share "
                            "any space"
                        ),
                        object_id=actor_id,
                        context={"target_actor_id": target_actor_id},
                    )
                )

        return ValidationResult(
            issues=issues,
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
        )
