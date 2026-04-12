"""
This module defines Action and related classes for modeling changes in the world.

An Action is a discrete, intentional change that an actor may perform within a
world and a specific space. Actions are:
- bound to an actor (the performer) and a location (space_id, world_id)
- constrained by the rules of the space/world and the actor's perception
- capable of consuming and producing resources
- capable of modifying space/world state

Core specs addressed: A-11 (manipulability), A-12 (objectives), P-2 (extensibility),
F-1 (canonical serialization).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .base import ModelObject, RelationMap

JsonMap = Dict[str, Any]
ObjectId = str


@dataclass
class ResourceEffect:
    """Describes how an action affects a specific resource.

    A resource effect may be:
    - consumption: removing a quantity from the world/space
    - production: adding a quantity to the world/space
    - transfer: moving a quantity from one location/actor to another
    """

    resource_id: ObjectId
    effect_type: str  # "consume", "produce", "transfer"
    quantity: float = 1.0
    source_id: Optional[ObjectId] = None  # originating location or actor
    target_id: Optional[ObjectId] = None  # destination location or actor
    metadata: JsonMap = field(default_factory=dict)

    def to_dict(self) -> JsonMap:
        """Serialize the resource effect."""
        return {
            "resource_id": self.resource_id,
            "effect_type": self.effect_type,
            "quantity": self.quantity,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResourceEffect":
        """Deserialize a resource effect."""
        return cls(
            resource_id=str(data["resource_id"]),
            effect_type=str(data.get("effect_type", "consume")),
            quantity=float(data.get("quantity", 1.0)),
            source_id=str(data["source_id"]) if data.get("source_id") else None,
            target_id=str(data["target_id"]) if data.get("target_id") else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ActionPrerequisite:
    """A condition that must be satisfied for an action to be admissible.

    Prerequisites may be:
    - resource requirements (actor must have minimum quantity)
    - perception requirements (actor must perceive a certain state)
    - space rules (space or world restricts action)
    - actor capability (actor must have a certain attribute/role/tag)
    """

    prerequisite_type: str  # "resource", "perception", "space_rule", "capability"
    field_name: str  # which attribute or condition
    required_value: Any = None  # required quantity, perceived state, etc.
    metadata: JsonMap = field(default_factory=dict)

    def to_dict(self) -> JsonMap:
        """Serialize the prerequisite."""
        return {
            "prerequisite_type": self.prerequisite_type,
            "field_name": self.field_name,
            "required_value": self.required_value,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ActionPrerequisite":
        """Deserialize a prerequisite."""
        return cls(
            prerequisite_type=str(data.get("prerequisite_type", "resource")),
            field_name=str(data["field_name"]),
            required_value=data.get("required_value"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class Action(ModelObject):
    """A discrete, intentional change that an actor may perform in a world/space.

    An action is bound to:
    - an actor (the performer)
    - a world and space (the location where it occurs)
    - a set of resource effects (what is consumed/produced)
    - a set of prerequisites (what must be true for the action to be admissible)
    - optional state changes (modifications to space/world/actor state)

    An action is constrained by:
    - space and world rules (spatial/contextual validation)
    - the actor's perception (the actor can only perform actions it perceives as feasible)
    - the actor's resources and capabilities
    """

    object_type: str = "action"
    actor_id: ObjectId = ""
    world_id: ObjectId = ""
    space_id: ObjectId = ""
    action_type: str = "generic"  # e.g., "move", "consume", "interact", "transform"
    resource_effects: List[ResourceEffect] = field(default_factory=list)
    prerequisites: List[ActionPrerequisite] = field(default_factory=list)
    outcome_description: str = ""  # human-readable description of what the action does
    state_changes: JsonMap = field(default_factory=dict)  # modifications to state

    def __post_init__(self) -> None:
        if self.object_type != "action":
            self.object_type = "action"
        if not self.id:
            raise ValueError("Action id cannot be empty")
        if not self.actor_id:
            raise ValueError("Action actor_id cannot be empty")
        if not self.world_id:
            raise ValueError("Action world_id cannot be empty")
        if not self.space_id:
            raise ValueError("Action space_id cannot be empty")
        if not self.action_type:
            raise ValueError("Action type cannot be empty")

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the action."""
        base = super().to_dict()
        base.update(
            {
                "actor_id": self.actor_id,
                "world_id": self.world_id,
                "space_id": self.space_id,
                "action_type": self.action_type,
                "resource_effects": [
                    re.to_dict()
                    for re in sorted(
                        self.resource_effects,
                        key=lambda x: (x.resource_id, x.effect_type),
                    )
                ],
                "prerequisites": [
                    p.to_dict()
                    for p in sorted(
                        self.prerequisites,
                        key=lambda x: (x.prerequisite_type, x.field_name),
                    )
                ],
                "outcome_description": self.outcome_description,
                "state_changes": dict(sorted(self.state_changes.items())),
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Action":
        """Reconstruct an action from its canonical representation."""
        base_obj = ModelObject.from_dict(data)
        return cls(
            id=base_obj.id,
            object_type=base_obj.object_type,
            schema_version=base_obj.schema_version,
            attributes=base_obj.attributes,
            relations=base_obj.relations,
            state=base_obj.state,
            context=base_obj.context,
            provenance=base_obj.provenance,
            actor_id=str(data["actor_id"]),
            world_id=str(data["world_id"]),
            space_id=str(data["space_id"]),
            action_type=str(data.get("action_type") or "generic"),
            resource_effects=[
                ResourceEffect.from_dict(re_data)
                for re_data in (data.get("resource_effects") or [])
            ],
            prerequisites=[
                ActionPrerequisite.from_dict(p_data)
                for p_data in (data.get("prerequisites") or [])
            ],
            outcome_description=str(data.get("outcome_description") or ""),
            state_changes=dict(data.get("state_changes") or {}),
        )

    def add_resource_effect(self, effect: ResourceEffect) -> None:
        """Add a resource effect to this action."""
        self.resource_effects.append(effect)

    def add_prerequisite(self, prerequisite: ActionPrerequisite) -> None:
        """Add a prerequisite to this action."""
        self.prerequisites.append(prerequisite)

    def set_state_change(self, key: str, value: Any) -> None:
        """Set a state change for this action."""
        if not key:
            raise ValueError("State change key cannot be empty")
        self.state_changes[key] = value
