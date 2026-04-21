"""Projection layer built from actions, perceptions, and resources.

Projection is a domain construct that derives explicit assumption sets from an
action considered under one actor-specific perception and a set of available
resources. Strategy nodes can later be built from these assumptions, but that
second-order strategizing does not belong here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from .actions import Action
from .base import JsonMap, ObjectId, _canonical_json_map, _require_non_null_string
from .perception import Perception, VALID_EPISTEMIC_STATUSES
from .resources import Resource

VALID_ACTION_PROJECTION_STATUSES: frozenset[str] = frozenset(
    {"blocked", "partial", "projected"}
)


def _evaluate_projection_requirements(
    action: Action,
    perception: Perception,
    *,
    resource_ids: Iterable[str],
) -> dict[str, Any]:
    """Evaluate baseline projection assumptions and status inputs."""
    resource_id_set = set(resource_ids)
    actor_match = action.actor_id == perception.actor_id

    assumption_payloads: list[dict[str, Any]] = [
        {
            "assumption_id": f"{action.id}:actor_binding",
            "assumption_type": "actor_binding",
            "description": "Action actor matches projection perception actor.",
            "subject_id": action.actor_id,
            "satisfied": actor_match,
            "rationale": (
                "Projection is actor-consistent."
                if actor_match
                else "Action actor and perception actor differ."
            ),
        },
        {
            "assumption_id": f"{action.id}:source_context",
            "assumption_type": "perception_context",
            "description": (
                "Projection is built from a perception context rather than world truth."
            ),
            "subject_id": perception.id,
            "satisfied": True,
            "rationale": "Perception is the explicit input basis for this projection.",
            "metadata": {"source_id": perception.source_id},
        },
        {
            "assumption_id": f"{action.id}:space_binding",
            "assumption_type": "space_binding",
            "description": "Action remains bound to its declared space during projection.",
            "subject_id": action.space_id,
            "satisfied": None,
            "rationale": (
                "Spatial feasibility resolution is deferred to later "
                "validation/projection stages."
            ),
        },
    ]

    missing_required_resources = False
    for effect in action.resource_effects:
        effect_requires_resource = effect.effect_type in {"consume", "transfer"}
        resource_available = effect.resource_id in resource_id_set
        if effect_requires_resource and not resource_available:
            missing_required_resources = True
        assumption_payloads.append(
            {
                "assumption_id": (
                    f"{action.id}:effect:{effect.resource_id}:{effect.effect_type}"
                ),
                "assumption_type": "resource_effect",
                "description": (
                    "Action resource effect is projected against the supplied "
                    "resource set."
                ),
                "subject_id": effect.resource_id,
                "satisfied": (resource_available if effect_requires_resource else None),
                "rationale": (
                    "Required resource is present in the supplied projection set."
                    if effect_requires_resource and resource_available
                    else (
                        "Required resource is missing from the supplied projection set."
                        if effect_requires_resource
                        else (
                            "Produced resources do not require prior availability "
                            "in this projection layer."
                        )
                    )
                ),
                "metadata": {
                    "effect_type": effect.effect_type,
                    "quantity": effect.quantity,
                    "source_id": effect.source_id,
                    "target_id": effect.target_id,
                },
            }
        )

    for prerequisite in action.prerequisites:
        assumption_payloads.append(
            {
                "assumption_id": (
                    f"{action.id}:prerequisite:{prerequisite.prerequisite_type}:"
                    f"{prerequisite.field_name}"
                ),
                "assumption_type": "prerequisite",
                "description": (
                    "Action prerequisite must be resolved by a later validation "
                    "or inference step."
                ),
                "subject_id": prerequisite.field_name,
                "satisfied": None,
                "rationale": (
                    "This projection layer records prerequisites but does not resolve "
                    "them generically."
                ),
                "metadata": {
                    "prerequisite_type": prerequisite.prerequisite_type,
                    "required_value": prerequisite.required_value,
                },
            }
        )

    return {
        "actor_match": actor_match,
        "missing_required_resources": missing_required_resources,
        "assumption_payloads": assumption_payloads,
    }


def _validate_action_projection_status(status: str) -> None:
    if status not in VALID_ACTION_PROJECTION_STATUSES:
        raise ValueError(
            f"Invalid action projection status: '{status}'. "
            f"Must be one of {sorted(VALID_ACTION_PROJECTION_STATUSES)}."
        )


def _validate_epistemic_status(status: str) -> None:
    if status not in VALID_EPISTEMIC_STATUSES:
        raise ValueError(
            f"Invalid epistemic status: '{status}'. "
            f"Must be one of {sorted(VALID_EPISTEMIC_STATUSES)}."
        )


def _normalize_optional_bool(value: Any, *, field_name: str) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a bool or None")


@dataclass
class ProjectionAssumption:
    """One explicit assumption extracted during action projection."""

    assumption_id: str
    assumption_type: str
    description: str
    subject_id: Optional[ObjectId] = None
    epistemic_status: str = "projected"
    satisfied: Optional[bool] = None
    rationale: str = ""
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.assumption_id:
            raise ValueError("ProjectionAssumption assumption_id cannot be empty")
        if not self.assumption_type:
            raise ValueError("ProjectionAssumption assumption_type cannot be empty")
        if not self.description:
            raise ValueError("ProjectionAssumption description cannot be empty")
        _validate_epistemic_status(self.epistemic_status)

    def to_dict(self) -> JsonMap:
        """Serialize the assumption in canonical form."""
        return {
            "assumption_id": self.assumption_id,
            "assumption_type": self.assumption_type,
            "description": self.description,
            "subject_id": self.subject_id,
            "epistemic_status": self.epistemic_status,
            "satisfied": self.satisfied,
            "rationale": self.rationale,
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectionAssumption":
        """Reconstruct an assumption from serialized data."""
        return cls(
            assumption_id=_require_non_null_string(data, "assumption_id"),
            assumption_type=_require_non_null_string(data, "assumption_type"),
            description=_require_non_null_string(data, "description"),
            subject_id=str(data["subject_id"]) if data.get("subject_id") else None,
            epistemic_status=str(data.get("epistemic_status") or "projected"),
            satisfied=_normalize_optional_bool(
                data.get("satisfied"),
                field_name="ProjectionAssumption.satisfied",
            ),
            rationale=str(data.get("rationale") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ActionProjection:
    """Projection result for one action under one perception and resource set."""

    action_id: ObjectId
    actor_id: ObjectId
    source_perception_id: ObjectId
    source_id: ObjectId
    status: str = "projected"
    resource_ids: list[ObjectId] = field(default_factory=list)
    assumptions: list[ProjectionAssumption] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("ActionProjection action_id cannot be empty")
        if not self.actor_id:
            raise ValueError("ActionProjection actor_id cannot be empty")
        if not self.source_perception_id:
            raise ValueError("ActionProjection source_perception_id cannot be empty")
        if not self.source_id:
            raise ValueError("ActionProjection source_id cannot be empty")
        _validate_action_projection_status(self.status)

    def to_dict(self) -> JsonMap:
        """Serialize the action projection in canonical form."""
        return {
            "action_id": self.action_id,
            "actor_id": self.actor_id,
            "source_perception_id": self.source_perception_id,
            "source_id": self.source_id,
            "status": self.status,
            "resource_ids": sorted(self.resource_ids),
            "assumptions": [
                assumption.to_dict()
                for assumption in sorted(
                    self.assumptions,
                    key=lambda assumption: assumption.assumption_id,
                )
            ],
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ActionProjection":
        """Reconstruct an action projection from serialized data."""
        return cls(
            action_id=_require_non_null_string(data, "action_id"),
            actor_id=_require_non_null_string(data, "actor_id"),
            source_perception_id=_require_non_null_string(data, "source_perception_id"),
            source_id=_require_non_null_string(data, "source_id"),
            status=str(data.get("status") or "projected"),
            resource_ids=[str(item) for item in (data.get("resource_ids") or [])],
            assumptions=[
                ProjectionAssumption.from_dict(raw_assumption)
                for raw_assumption in (data.get("assumptions") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ProjectionBatch:
    """Deterministic batch of action projections for one perception context."""

    actor_id: ObjectId
    source_perception_id: ObjectId
    source_id: ObjectId
    projections: list[ActionProjection] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("ProjectionBatch actor_id cannot be empty")
        if not self.source_perception_id:
            raise ValueError("ProjectionBatch source_perception_id cannot be empty")
        if not self.source_id:
            raise ValueError("ProjectionBatch source_id cannot be empty")

    def to_dict(self) -> JsonMap:
        """Serialize the batch in canonical form."""
        return {
            "actor_id": self.actor_id,
            "source_perception_id": self.source_perception_id,
            "source_id": self.source_id,
            "projections": [
                projection.to_dict()
                for projection in sorted(
                    self.projections,
                    key=lambda projection: projection.action_id,
                )
            ],
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectionBatch":
        """Reconstruct a projection batch from serialized data."""
        return cls(
            actor_id=_require_non_null_string(data, "actor_id"),
            source_perception_id=_require_non_null_string(data, "source_perception_id"),
            source_id=_require_non_null_string(data, "source_id"),
            projections=[
                ActionProjection.from_dict(raw_projection)
                for raw_projection in (data.get("projections") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )


class ProjectionTool(ABC):
    """Contract for deriving assumptions from actions and perceptions."""

    @abstractmethod
    def project_action(
        self,
        action: Action,
        perception: Perception,
        *,
        resources: Iterable[Resource] = (),
    ) -> ActionProjection:
        """Project one action into an explicit assumption set."""

    def project_actions(
        self,
        actions: Iterable[Action],
        perception: Perception,
        *,
        resources: Iterable[Resource] = (),
    ) -> ProjectionBatch:
        """Project multiple actions in a deterministic batch."""
        resource_list = list(resources)
        projections = [
            self.project_action(action, perception, resources=resource_list)
            for action in sorted(actions, key=lambda action: action.id)
        ]
        return ProjectionBatch(
            actor_id=perception.actor_id,
            source_perception_id=perception.id,
            source_id=perception.source_id,
            projections=projections,
            metadata={"projection_basis": "perception"},
        )


class DefaultProjectionTool(ProjectionTool):
    """Minimal projection tool based on action, perception, and resource inputs.

    This default tool does not execute actions and does not build strategy nodes.
    It only externalizes the assumptions that a later strategy-building step may
    consume.
    """

    def project_action(
        self,
        action: Action,
        perception: Perception,
        *,
        resources: Iterable[Resource] = (),
    ) -> ActionProjection:
        resource_index = {resource.id: resource for resource in resources}
        evaluation = _evaluate_projection_requirements(
            action,
            perception,
            resource_ids=resource_index.keys(),
        )
        assumptions = [
            ProjectionAssumption.from_dict(payload)
            for payload in evaluation["assumption_payloads"]
        ]

        status = "projected"
        if not evaluation["actor_match"]:
            status = "blocked"
        elif evaluation["missing_required_resources"]:
            status = "partial"

        return ActionProjection(
            action_id=action.id,
            actor_id=perception.actor_id,
            source_perception_id=perception.id,
            source_id=perception.source_id,
            status=status,
            resource_ids=sorted(resource_index.keys()),
            assumptions=assumptions,
            metadata={"projection_basis": "perception"},
        )


def project_actions(
    actions: Iterable[Action],
    perception: Perception,
    *,
    resources: Iterable[Resource] = (),
    projection_tool: Optional[ProjectionTool] = None,
) -> ProjectionBatch:
    """Project multiple actions into assumption sets using the provided tool."""
    resolved_tool = projection_tool or DefaultProjectionTool()
    return resolved_tool.project_actions(actions, perception, resources=resources)
