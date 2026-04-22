"""Temporal validator enforcing basic coexistence constraints."""

from __future__ import annotations

from datetime import datetime
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


class TemporalValidator:
    """Validate actor coexistence at a given interaction time."""

    @property
    def name(self) -> str:
        return "temporal"

    def validate(self, obj: Any, context: ValidationContext) -> ValidationResult:
        issues: list[ValidationIssue] = []

        actor_id = ""
        if isinstance(obj, Action):
            actor_id = obj.actor_id
        elif isinstance(obj, Mapping):
            actor_id = str(obj.get("actor_id") or "")

        if not actor_id:
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="TEMP-NO-ACTOR",
                        severity=SEVERITY_WARNING,
                        message="Temporal validation skipped because actor_id is missing",
                    )
                ],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        interaction_time = context.metadata.get("interaction_time")
        if interaction_time is None:
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="TEMP-NO-TIME",
                        severity=SEVERITY_WARNING,
                        message=(
                            "Temporal validation skipped because interaction_time "
                            "is missing"
                        ),
                    )
                ],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        world = context.metadata.get("world")
        validity = self._resolve_validity_for_actor(
            actor_id=actor_id,
            world=world if isinstance(world, World) else None,
            metadata=context.metadata,
        )

        if validity is None:
            return ValidationResult(
                issues=[
                    ValidationIssue(
                        code="TEMP-NO-VALIDITY",
                        severity=SEVERITY_WARNING,
                        message=(
                            "No temporal validity found for actor; coexistence "
                            "cannot be proven"
                        ),
                        object_id=actor_id,
                    )
                ],
                stage=context.stage or self.name,
                policy_mode=context.policy_mode,
            )

        start = validity.get("start")
        end = validity.get("end")
        if not self._is_within_interval(interaction_time, start, end):
            issues.append(
                ValidationIssue(
                    code="TEMP-OUTSIDE-VALIDITY",
                    severity=SEVERITY_ERROR,
                    message=(
                        f"Interaction time {interaction_time!r} is outside actor "
                        f"validity interval [{start!r}, {end!r}]"
                    ),
                    object_id=actor_id,
                )
            )

        return ValidationResult(
            issues=issues,
            stage=context.stage or self.name,
            policy_mode=context.policy_mode,
        )

    def _resolve_validity_for_actor(
        self,
        *,
        actor_id: str,
        world: World | None,
        metadata: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        raw_mapping = metadata.get("actor_validity")
        if isinstance(raw_mapping, Mapping):
            candidate = raw_mapping.get(actor_id)
            if isinstance(candidate, Mapping):
                return candidate

        if world is None:
            return None

        actor = world.model_registry.get(actor_id)
        if actor is None:
            return None

        validity = actor.attributes.get("validity")
        if isinstance(validity, Mapping):
            return validity
        return None

    def _is_within_interval(self, value: Any, start: Any, end: Any) -> bool:
        normalized_value = self._normalize_temporal_value(value)
        normalized_start = self._normalize_temporal_value(start)
        normalized_end = self._normalize_temporal_value(end)

        if normalized_value is None:
            return False

        if normalized_start is not None and normalized_value < normalized_start:
            return False
        if normalized_end is not None and normalized_value > normalized_end:
            return False
        return True

    def _normalize_temporal_value(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).timestamp()
            except ValueError:
                try:
                    return float(value)
                except ValueError as exc:
                    raise ValueError(f"Unsupported temporal value: {value!r}") from exc
        raise ValueError(f"Unsupported temporal value type: {type(value).__name__}")
