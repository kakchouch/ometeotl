"""
This module defines the World class.

World inherits from Space and represents the root semantic space of the
model. It provides the primary ontological layer in which the simulation
is grounded. A world may operate as a standalone space or support the
existence of other derived or nested spaces.

Objects directly supported by a world are treated as minimal objects and
must be registered in the minimal registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional
from .base import ModelObject
from .spaces import Space, SpaceObjectGraph, SpaceObjectMembership
from .space_relations import SpaceRelation, SpaceRelationGraph
from .registry import MinimalModelRegistry
from .objects import GenericObject

JsonMap = Dict[str, Any]
ObjectId = str
SpaceId = str


@dataclass
class World(Space):
    """
    World inherits from Space and represents the root semantic space of the
    model. It provides the primary ontological layer in which the simulation
    is grounded. A world may operate as a standalone space or support the
    existence of other derived or nested spaces.

    Objects directly supported by a world are treated as minimal objects and
    must be registered in the minimal registry.
    """

    object_type: str = "world"
    is_root_world: bool = True
    space_object_graph: SpaceObjectGraph = field(default_factory=SpaceObjectGraph)
    space_relation_graph: SpaceRelationGraph = field(default_factory=SpaceRelationGraph)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.object_type = "world"
        self.attributes["kind"] = "world"
        self.attributes["is_root_world"] = self.is_root_world

    # --- Sub-space management -----------------------------------------------

    def add_space(self, space: Space) -> None:
        """Add a sub-space to this world's space object graph."""
        self.space_object_graph.add_space(space)

    def get_space(self, space_id: SpaceId) -> Optional[Space]:
        """Retrieve a sub-space by ID, or None if it does not exist."""
        return self.space_object_graph.get_space(space_id)

    def add_space_relation(self, relation: SpaceRelation) -> None:
        """Add a directional or symmetric relation between two sub-spaces."""
        self.space_relation_graph.add_relation(relation)

    # --- Object placement ---------------------------------------------------

    def place_object(
        self,
        object_id: ObjectId,
        space_id: SpaceId,
        role: str = "occupies",
    ) -> None:
        """Declare the presence of an object in a given sub-space.

        The target space must have been added to this world beforehand via
        ``add_space``.
        """
        membership = SpaceObjectMembership(
            object_id=object_id,
            space_id=space_id,
            role=role,
        )
        self.space_object_graph.add_object_membership(membership)

    # --- Registry operations ------------------------------------------------

    def register_object(self, obj: GenericObject) -> None:
        """Register a minimal object in the shared minimal registry."""
        MinimalModelRegistry.register(obj)

    def unregister_object(self, obj_id: ObjectId) -> None:
        """Remove an object from the shared minimal registry."""
        MinimalModelRegistry.unregister(obj_id)

    # --- Serialization ------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the world.

        Extends the base Space serialization with sub-space graph data
        (SpaceObjectGraph and SpaceRelationGraph). Satisfies F-1, F-2, F-3.
        """
        base = super().to_dict()
        base["space_object_graph"] = self.space_object_graph.to_dict()
        base["space_relation_graph"] = self.space_relation_graph.to_dict()
        return base

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "World":
        """Reconstruct a World from its canonical dictionary representation."""
        payload = dict(data)
        payload["object_type"] = payload.get("object_type") or "world"
        base_obj = ModelObject.from_dict(payload)
        attributes = base_obj.attributes
        is_root_world = bool(attributes.get("is_root_world", True))
        return cls(
            id=base_obj.id,
            object_type=base_obj.object_type,
            schema_version=base_obj.schema_version,
            attributes=attributes,
            relations=base_obj.relations,
            state=base_obj.state,
            context=base_obj.context,
            provenance=base_obj.provenance,
            is_root_world=is_root_world,
            space_object_graph=SpaceObjectGraph.from_dict(
                data.get("space_object_graph") or {}
            ),
            space_relation_graph=SpaceRelationGraph.from_dict(
                data.get("space_relation_graph") or {}
            ),
        )
