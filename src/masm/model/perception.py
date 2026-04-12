"""
This module defines Perception and its constituent perceived elements.

A Perception is an actor-specific, partial, and potentially distorted
representation of a World or Space. It is the epistemic layer through
which actors reason and decide (specs A-9, A-10, F-5, F-14).

Each perceived element carries:
- a deep copy of the source data (insulated from world mutations);
- an epistemic status quantifying the actor's degree of confidence:
    "certain"    — directly observed, no uncertainty;
    "believed"   — inferred or remembered, probably true;
    "hypothesis" — speculative, may or may not hold;
    "projected"  — anticipated based on a model but not observed;
    "error"      — identified as incorrect (diagnosed hallucination).
- a noise_metadata dict documenting any distortion applied by a Sensor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .spaces import Space, SpaceObjectMembership
from .space_relations import SpaceRelation

JsonMap = Dict[str, Any]
ObjectId = str
SpaceId = str

VALID_EPISTEMIC_STATUSES: frozenset = frozenset(
    {"certain", "believed", "hypothesis", "projected", "error"}
)


def _validate_epistemic_status(status: str) -> None:
    if status not in VALID_EPISTEMIC_STATUSES:
        raise ValueError(
            f"Invalid epistemic status: '{status}'. "
            f"Must be one of {sorted(VALID_EPISTEMIC_STATUSES)}."
        )


# ---------------------------------------------------------------------------
# Perceived element wrappers
# ---------------------------------------------------------------------------


@dataclass
class PerceivedSpace:
    """A copy of a Space as perceived by a given actor through a Sensor.

    The space value is a deep copy; changes to the world do not propagate
    here after sensing.
    """

    space: Space
    epistemic_status: str = "certain"
    noise_metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_epistemic_status(self.epistemic_status)

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the perceived space."""
        return {
            "space": self.space.to_dict(),
            "epistemic_status": self.epistemic_status,
            "noise_metadata": dict(sorted(self.noise_metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PerceivedSpace":
        """Reconstruct a PerceivedSpace from its canonical representation."""
        return cls(
            space=Space.from_dict(data["space"]),
            epistemic_status=str(data.get("epistemic_status", "certain")),
            noise_metadata=dict(data.get("noise_metadata", {})),
        )


@dataclass
class PerceivedMembership:
    """A copy of a SpaceObjectMembership as perceived by a given actor."""

    membership: SpaceObjectMembership
    epistemic_status: str = "certain"
    noise_metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_epistemic_status(self.epistemic_status)

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the perceived membership."""
        return {
            "membership": self.membership.to_dict(),
            "epistemic_status": self.epistemic_status,
            "noise_metadata": dict(sorted(self.noise_metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PerceivedMembership":
        """Reconstruct a PerceivedMembership from its canonical representation."""
        return cls(
            membership=SpaceObjectMembership.from_dict(data["membership"]),
            epistemic_status=str(data.get("epistemic_status", "certain")),
            noise_metadata=dict(data.get("noise_metadata", {})),
        )


@dataclass
class PerceivedRelation:
    """A copy of a SpaceRelation as perceived by a given actor."""

    relation: SpaceRelation
    epistemic_status: str = "certain"
    noise_metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_epistemic_status(self.epistemic_status)

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the perceived relation."""
        return {
            "relation": self.relation.to_dict(),
            "epistemic_status": self.epistemic_status,
            "noise_metadata": dict(sorted(self.noise_metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PerceivedRelation":
        """Reconstruct a PerceivedRelation from its canonical representation."""
        return cls(
            relation=SpaceRelation.from_dict(data["relation"]),
            epistemic_status=str(data.get("epistemic_status", "certain")),
            noise_metadata=dict(data.get("noise_metadata", {})),
        )


# ---------------------------------------------------------------------------
# Perception
# ---------------------------------------------------------------------------


@dataclass
class Perception:
    """Actor-specific partial representation of a World or Space.

    A Perception is built by a Sensor from a World instance. It contains
    only the subset of world elements the sensor chose to copy, and each
    element may be distorted by noise rules. The epistemic status of each
    element records the actor's degree of confidence in that element.

    Core specs: A-9 (partial perception), A-10 (reality/perception
    dissociation), A-11 (manipulability), F-5 (LLM view), F-14 (epistemic
    validation).
    """

    id: str
    actor_id: ObjectId
    source_id: ObjectId  # ID of the world or space this perception is derived from
    schema_version: str = "1.0"
    timestamp: Optional[Any] = None
    perceived_spaces: Dict[SpaceId, PerceivedSpace] = field(default_factory=dict)
    perceived_memberships: List[PerceivedMembership] = field(default_factory=list)
    perceived_relations: List[PerceivedRelation] = field(default_factory=list)
    context: JsonMap = field(default_factory=dict)
    provenance: JsonMap = field(default_factory=dict)

    # --- Query API ----------------------------------------------------------

    def get_perceived_space(self, space_id: SpaceId) -> Optional[PerceivedSpace]:
        """Return the perceived version of a space, or None if not perceived."""
        return self.perceived_spaces.get(space_id)

    def memberships_for_object(self, object_id: ObjectId) -> List[PerceivedMembership]:
        """Return all perceived memberships associated with a given object ID."""
        return [
            pm
            for pm in self.perceived_memberships
            if pm.membership.object_id == object_id
        ]

    def memberships_in_space(self, space_id: SpaceId) -> List[PerceivedMembership]:
        """Return all perceived memberships whose space is the given space ID."""
        return [
            pm
            for pm in self.perceived_memberships
            if pm.membership.space_id == space_id
        ]

    def relations_for_space(self, space_id: SpaceId) -> List[PerceivedRelation]:
        """Return all perceived relations involving the given space ID."""
        return [
            pr
            for pr in self.perceived_relations
            if (
                pr.relation.source_space_id == space_id
                or pr.relation.target_space_id == space_id
            )
        ]

    # --- Serialization ------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the perception (satisfies F-1, F-2, F-3)."""
        return {
            "id": self.id,
            "object_type": "perception",
            "schema_version": self.schema_version,
            "actor_id": self.actor_id,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "perceived_spaces": {
                space_id: ps.to_dict()
                for space_id, ps in sorted(self.perceived_spaces.items())
            },
            "perceived_memberships": [
                pm.to_dict() for pm in self.perceived_memberships
            ],
            "perceived_relations": [pr.to_dict() for pr in self.perceived_relations],
            "context": dict(sorted(self.context.items())),
            "provenance": dict(sorted(self.provenance.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Perception":
        """Reconstruct a Perception from its canonical dictionary representation."""
        return cls(
            id=str(data["id"]),
            actor_id=str(data["actor_id"]),
            source_id=str(data["source_id"]),
            schema_version=str(data.get("schema_version", "1.0")),
            timestamp=data.get("timestamp"),
            perceived_spaces={
                space_id: PerceivedSpace.from_dict(ps_data)
                for space_id, ps_data in data.get("perceived_spaces", {}).items()
            },
            perceived_memberships=[
                PerceivedMembership.from_dict(pm_data)
                for pm_data in data.get("perceived_memberships", [])
            ],
            perceived_relations=[
                PerceivedRelation.from_dict(pr_data)
                for pr_data in data.get("perceived_relations", [])
            ],
            context=dict(data.get("context", {})),
            provenance=dict(data.get("provenance", {})),
        )
