"""Projection layer built from actions, perceptions, and resources.

Projection is a domain construct that derives explicit assumption sets from an
action considered under one actor-specific perception and a set of available
resources. Strategy nodes can later be built from these assumptions, but that
second-order strategizing does not belong here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from .actions import Action
from .resources import Resource
from .base import JsonMap, ObjectId, _canonical_json_map, _require_non_null_string
from .perception import (
    Perception,
    PerceivedMembership,
    VALID_EPISTEMIC_STATUSES,
    _validate_epistemic_status,
)
from .spaces import SpaceObjectMembership

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
    for idx, effect in enumerate(action.resource_effects):
        effect_requires_resource = effect.effect_type in {"consume", "transfer"}
        resource_available = effect.resource_id in resource_id_set
        if effect_requires_resource and resource_available:
            required_space_id = effect.source_id or action.space_id
            resource_in_space = any(
                pm.membership.object_id == effect.resource_id
                and pm.membership.space_id == required_space_id
                for pm in perception.perceived_memberships
            )
            if not resource_in_space:
                resource_available = False
        if effect_requires_resource and not resource_available:
            missing_required_resources = True
        assumption_payloads.append(
            {
                "assumption_id": (
                    f"{action.id}:effect:{idx}:{effect.resource_id}:{effect.effect_type}"
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

    for idx, prerequisite in enumerate(action.prerequisites):
        assumption_payloads.append(
            {
                "assumption_id": (
                    f"{action.id}:prerequisite:{idx}:{prerequisite.prerequisite_type}:"
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


def _normalize_optional_bool(value: Any, *, field_name: str) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a bool or None")


def _mark_perception_as_projected(perception: Perception) -> None:
    for perceived_space in perception.perceived_spaces.values():
        perceived_space.epistemic_status = "projected"
    for perceived_membership in perception.perceived_memberships:
        perceived_membership.epistemic_status = "projected"
    for perceived_relation in perception.perceived_relations:
        perceived_relation.epistemic_status = "projected"


def _resolve_known_space_id(
    perception: Perception,
    candidate_space_id: Optional[ObjectId],
    *,
    fallback_space_id: ObjectId,
) -> Optional[ObjectId]:
    if candidate_space_id and candidate_space_id in perception.perceived_spaces:
        return candidate_space_id
    if fallback_space_id in perception.perceived_spaces:
        return fallback_space_id
    return None


def _remove_perceived_memberships(
    perception: Perception,
    *,
    object_id: ObjectId,
    space_id: ObjectId,
    role: str = "occupies",
) -> int:
    original_count = len(perception.perceived_memberships)
    perception.perceived_memberships = [
        perceived_membership
        for perceived_membership in perception.perceived_memberships
        if not (
            perceived_membership.membership.object_id == object_id
            and perceived_membership.membership.space_id == space_id
            and perceived_membership.membership.role == role
        )
    ]
    return original_count - len(perception.perceived_memberships)


def _has_perceived_membership(
    perception: Perception,
    *,
    object_id: ObjectId,
    space_id: ObjectId,
    role: str,
) -> bool:
    return any(
        perceived_membership.membership.object_id == object_id
        and perceived_membership.membership.space_id == space_id
        and perceived_membership.membership.role == role
        for perceived_membership in perception.perceived_memberships
    )


def _append_projected_membership(
    perception: Perception,
    *,
    object_id: ObjectId,
    space_id: ObjectId,
    generating_action_id: ObjectId,
    role: str = "occupies",
) -> bool:
    if _has_perceived_membership(
        perception,
        object_id=object_id,
        space_id=space_id,
        role=role,
    ):
        return False

    perception.perceived_memberships.append(
        PerceivedMembership(
            membership=SpaceObjectMembership(
                object_id=object_id,
                space_id=space_id,
                role=role,
                metadata={"projected_by_action_id": generating_action_id},
            ),
            epistemic_status="projected",
            noise_metadata={"projection_action_id": generating_action_id},
        )
    )
    return True


def _projected_perception_id(perception: Perception, action: Action) -> str:
    return f"projection-{perception.id}-{action.id}"


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
class ProjectedPerceptionChange:
    """One explicit change applied while projecting a successor perception."""

    change_id: str
    change_type: str
    subject_id: Optional[ObjectId] = None
    space_id: Optional[ObjectId] = None
    applied: Optional[bool] = None
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.change_id:
            raise ValueError("ProjectedPerceptionChange change_id cannot be empty")
        if not self.change_type:
            raise ValueError("ProjectedPerceptionChange change_type cannot be empty")

    def to_dict(self) -> JsonMap:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type,
            "subject_id": self.subject_id,
            "space_id": self.space_id,
            "applied": self.applied,
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectedPerceptionChange":
        return cls(
            change_id=_require_non_null_string(data, "change_id"),
            change_type=_require_non_null_string(data, "change_type"),
            subject_id=str(data["subject_id"]) if data.get("subject_id") else None,
            space_id=str(data["space_id"]) if data.get("space_id") else None,
            applied=_normalize_optional_bool(
                data.get("applied"),
                field_name="ProjectedPerceptionChange.applied",
            ),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ProjectedPerceptionState:
    """Projected successor perception derived from an action outcome."""

    source_perception_id: ObjectId
    generating_action_id: ObjectId
    perception: Perception
    changes: list[ProjectedPerceptionChange] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_perception_id:
            raise ValueError(
                "ProjectedPerceptionState source_perception_id cannot be empty"
            )
        if not self.generating_action_id:
            raise ValueError(
                "ProjectedPerceptionState generating_action_id cannot be empty"
            )
        if not self.perception.actor_id:
            raise ValueError("ProjectedPerceptionState perception actor_id is invalid")

    def to_dict(self) -> JsonMap:
        return {
            "source_perception_id": self.source_perception_id,
            "generating_action_id": self.generating_action_id,
            "perception": self.perception.to_dict(),
            "changes": [
                change.to_dict()
                for change in sorted(self.changes, key=lambda change: change.change_id)
            ],
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProjectedPerceptionState":
        perception_payload = data.get("perception")
        if not isinstance(perception_payload, Mapping):
            raise ValueError("ProjectedPerceptionState perception must be a mapping")
        return cls(
            source_perception_id=_require_non_null_string(data, "source_perception_id"),
            generating_action_id=_require_non_null_string(data, "generating_action_id"),
            perception=Perception.from_dict(perception_payload),
            changes=[
                ProjectedPerceptionChange.from_dict(raw_change)
                for raw_change in (data.get("changes") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )


def _build_projected_perception_state(
    action: Action,
    perception: Perception,
    resource_index: Optional[Mapping[str, "Resource"]] = None,
) -> ProjectedPerceptionState:
    projected_perception = copy.deepcopy(perception)
    projected_perception.id = _projected_perception_id(perception, action)
    _mark_perception_as_projected(projected_perception)

    provenance = dict(projected_perception.provenance)
    provenance.update(
        {
            "projection_basis": "perception",
            "source_perception_id": perception.id,
            "generating_action_id": action.id,
        }
    )
    projected_perception.provenance = _canonical_json_map(provenance)

    changes: list[ProjectedPerceptionChange] = []
    if action.state_changes:
        projected_state_changes = dict(
            projected_perception.context.get("projected_state_changes") or {}
        )
        projected_state_changes[action.id] = dict(action.state_changes)
        projected_perception.context["projected_state_changes"] = _canonical_json_map(
            projected_state_changes
        )

        context_updates = action.state_changes.get("context_updates")
        applied = isinstance(context_updates, Mapping)
        if applied:
            projected_perception.context.update(dict(context_updates))

        changes.append(
            ProjectedPerceptionChange(
                change_id=f"{action.id}:state_changes",
                change_type="state_changes",
                subject_id=action.id,
                applied=applied,
                metadata={"state_changes": dict(action.state_changes)},
            )
        )

    _resource_index: Mapping[str, Resource] = resource_index or {}

    for effect in action.resource_effects:
        resource_obj = _resource_index.get(effect.resource_id)
        is_stock = (
            resource_obj is not None
            and resource_obj.resource_mode == "stock"
            and effect.quantity != 1.0
        )

        if effect.effect_type == "consume":
            source_space_id = _resolve_known_space_id(
                projected_perception,
                effect.source_id,
                fallback_space_id=action.space_id,
            )
            if is_stock:
                stock_deltas = dict(
                    projected_perception.context.get("projected_stock_deltas") or {}
                )
                stock_deltas[effect.resource_id] = (
                    float(stock_deltas.get(effect.resource_id) or 0) - effect.quantity
                )
                projected_perception.context["projected_stock_deltas"] = (
                    _canonical_json_map(stock_deltas)
                )
                changes.append(
                    ProjectedPerceptionChange(
                        change_id=f"{action.id}:resource_effect:{idx}:{effect.resource_id}:consume",
                        change_type="resource_consume",
                        subject_id=effect.resource_id,
                        space_id=source_space_id,
                        applied=True,
                        metadata={"quantity": effect.quantity, "method": "stock_delta"},
                    )
                )
            else:
                removed_count = 0
                if source_space_id is not None:
                    removed_count = _remove_perceived_memberships(
                        projected_perception,
                        object_id=effect.resource_id,
                        space_id=source_space_id,
                    )
                changes.append(
                    ProjectedPerceptionChange(
                        change_id=f"{action.id}:resource_effect:{effect.resource_id}:consume",
                        change_type="resource_consume",
                        subject_id=effect.resource_id,
                        space_id=source_space_id,
                        applied=removed_count > 0,
                        metadata={
                            "quantity": effect.quantity,
                            "removed_membership_count": removed_count,
                        },
                    )
                )
            continue

        if effect.effect_type == "produce":
            target_space_id = _resolve_known_space_id(
                projected_perception,
                effect.target_id,
                fallback_space_id=action.space_id,
            )
            if is_stock:
                stock_deltas = dict(
                    projected_perception.context.get("projected_stock_deltas") or {}
                )
                stock_deltas[effect.resource_id] = (
                    float(stock_deltas.get(effect.resource_id) or 0) + effect.quantity
                )
                projected_perception.context["projected_stock_deltas"] = (
                    _canonical_json_map(stock_deltas)
                )
                changes.append(
                    ProjectedPerceptionChange(
                        change_id=f"{action.id}:resource_effect:{effect.resource_id}:produce",
                        change_type="resource_produce",
                        subject_id=effect.resource_id,
                        space_id=target_space_id,
                        applied=True,
                        metadata={"quantity": effect.quantity, "method": "stock_delta"},
                    )
                )
            else:
                produced = False
                if target_space_id is not None:
                    produced = _append_projected_membership(
                        projected_perception,
                        object_id=effect.resource_id,
                        space_id=target_space_id,
                        generating_action_id=action.id,
                    )
                changes.append(
                    ProjectedPerceptionChange(
                        change_id=f"{action.id}:resource_effect:{effect.resource_id}:produce",
                        change_type="resource_produce",
                        subject_id=effect.resource_id,
                        space_id=target_space_id,
                        applied=produced,
                        metadata={"quantity": effect.quantity},
                    )
                )
            continue

        if effect.effect_type == "transfer":
            source_space_id = _resolve_known_space_id(
                projected_perception,
                effect.source_id,
                fallback_space_id=action.space_id,
            )
            target_space_id = _resolve_known_space_id(
                projected_perception,
                effect.target_id,
                fallback_space_id=action.space_id,
            )
            if is_stock:
                stock_deltas = dict(
                    projected_perception.context.get("projected_stock_deltas") or {}
                )
                stock_deltas[effect.resource_id] = (
                    float(stock_deltas.get(effect.resource_id) or 0) - effect.quantity
                )
                projected_perception.context["projected_stock_deltas"] = (
                    _canonical_json_map(stock_deltas)
                )
                changes.append(
                    ProjectedPerceptionChange(
                        change_id=f"{action.id}:resource_effect:{effect.resource_id}:transfer",
                        change_type="resource_transfer",
                        subject_id=effect.resource_id,
                        space_id=target_space_id,
                        applied=True,
                        metadata={
                            "quantity": effect.quantity,
                            "method": "stock_delta",
                            "source_space_id": source_space_id,
                            "target_space_id": target_space_id,
                        },
                    )
                )
            else:
                removed_count = 0
                added = False
                if source_space_id is not None and target_space_id is not None:
                    removed_count = _remove_perceived_memberships(
                        projected_perception,
                        object_id=effect.resource_id,
                        space_id=source_space_id,
                    )
                    if removed_count > 0:
                        added = _append_projected_membership(
                            projected_perception,
                            object_id=effect.resource_id,
                            space_id=target_space_id,
                            generating_action_id=action.id,
                        )
                changes.append(
                    ProjectedPerceptionChange(
                        change_id=f"{action.id}:resource_effect:{effect.resource_id}:transfer",
                        change_type="resource_transfer",
                        subject_id=effect.resource_id,
                        space_id=target_space_id,
                        applied=removed_count > 0 and added,
                        metadata={
                            "quantity": effect.quantity,
                            "source_space_id": source_space_id,
                            "target_space_id": target_space_id,
                            "removed_membership_count": removed_count,
                        },
                    )
                )

    return ProjectedPerceptionState(
        source_perception_id=perception.id,
        generating_action_id=action.id,
        perception=projected_perception,
        changes=changes,
        metadata={"projection_basis": "perception"},
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
    projected_state: Optional[ProjectedPerceptionState] = None
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
            "projected_state": (
                self.projected_state.to_dict()
                if self.projected_state is not None
                else None
            ),
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
            projected_state=(
                ProjectedPerceptionState.from_dict(data["projected_state"])
                if data.get("projected_state") is not None
                else None
            ),
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

        projected_state = None
        if evaluation["actor_match"]:
            projected_state = _build_projected_perception_state(
                action, perception, resource_index
            )

        return ActionProjection(
            action_id=action.id,
            actor_id=perception.actor_id,
            source_perception_id=perception.id,
            source_id=perception.source_id,
            status=status,
            resource_ids=sorted(resource_index.keys()),
            assumptions=assumptions,
            projected_state=projected_state,
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
