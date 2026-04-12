"""
This module defines the World class.

World inherits from Space and represents the root semantic space of the
model. It provides the primary ontological layer in which the simulation
is grounded. A world may operate as a standalone space or support the
existence of other derived or nested spaces.

Objects directly supported by a world are treated as minimal objects and
    must be registered in the world-scoped registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from .base import ModelObject, ObjectId, JsonMap
from .spaces import Space, SpaceObjectGraph, SpaceObjectMembership
from .space_relations import SpaceRelation, SpaceRelationGraph
from .registry import WorldModelRegistry

SpaceId = str


@dataclass
class World(Space):
    """
    World inherits from Space and represents the root semantic space of the
    model. It provides the primary ontological layer in which the simulation
    is grounded. A world may operate as a standalone space or support the
    existence of other derived or nested spaces.

    Objects directly supported by a world are treated as minimal objects and
    must be registered in the world-scoped registry.
    """

    object_type: str = "world"
    is_root_world: bool = True
    space_object_graph: SpaceObjectGraph = field(default_factory=SpaceObjectGraph)
    space_relation_graph: SpaceRelationGraph = field(default_factory=SpaceRelationGraph)
    model_registry: WorldModelRegistry = field(default_factory=WorldModelRegistry)
    _authority_mode_enabled: bool = field(default=False, init=False, repr=False)
    _authority_token: Optional[str] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.object_type = "world"
        self.attributes["kind"] = "world"
        self.attributes["is_root_world"] = self.is_root_world
        self.model_registry.set_mutation_guard(self._assert_mutation_allowed)

    def enable_authority_mode(self, token: str) -> None:
        """Enable authoritative mutation mode.

        When enabled, mutating world APIs only accept calls that carry the
        expected authority token. This creates an explicit server-side
        boundary while keeping backward compatibility for local/in-process use
        when authority mode is disabled.
        """
        if not token:
            raise ValueError("Authority token cannot be empty")
        self._authority_mode_enabled = True
        self._authority_token = token

    def disable_authority_mode(self) -> None:
        """Disable authoritative mutation mode."""
        self._authority_mode_enabled = False
        self._authority_token = None

    def _assert_mutation_allowed(self, authority_token: Optional[str]) -> None:
        if not self._authority_mode_enabled:
            return
        if authority_token != self._authority_token:
            raise PermissionError(
                "World mutation denied: use the authoritative command interface"
            )

    # --- Sub-space management -----------------------------------------------

    def add_space(self, space: Space, authority_token: Optional[str] = None) -> None:
        """Add a sub-space to this world's space object graph."""
        self._assert_mutation_allowed(authority_token)
        self.space_object_graph.add_space(space)

    def get_space(self, space_id: SpaceId) -> Optional[Space]:
        """Retrieve a sub-space by ID, or None if it does not exist."""
        return self.space_object_graph.get_space(space_id)

    def add_space_relation(
        self, relation: SpaceRelation, authority_token: Optional[str] = None
    ) -> None:
        """Add a directional or symmetric relation between two sub-spaces."""
        self._assert_mutation_allowed(authority_token)
        self.space_relation_graph.add_relation(relation)

    # --- Object placement ---------------------------------------------------

    def place_object(
        self,
        object_id: ObjectId,
        space_id: SpaceId,
        role: str = "occupies",
        authority_token: Optional[str] = None,
    ) -> None:
        """Declare the presence of an object in a given sub-space.

        The target space must have been added to this world beforehand via
        ``add_space``.
        """
        self._assert_mutation_allowed(authority_token)
        membership = SpaceObjectMembership(
            object_id=object_id,
            space_id=space_id,
            role=role,
        )
        self.space_object_graph.add_object_membership(membership)

    # --- Registry operations ------------------------------------------------

    def register_object(
        self, obj: ModelObject, authority_token: Optional[str] = None
    ) -> None:
        """Register a minimal object in this world-scoped registry."""
        self._assert_mutation_allowed(authority_token)
        self.model_registry.register(obj, authority_token=authority_token)

    def unregister_object(
        self, obj_id: ObjectId, authority_token: Optional[str] = None
    ) -> None:
        """Remove an object from this world-scoped registry."""
        self._assert_mutation_allowed(authority_token)
        self.model_registry.unregister(obj_id, authority_token=authority_token)

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
            **base_obj._base_kwargs(),
            is_root_world=is_root_world,
            space_object_graph=SpaceObjectGraph.from_dict(
                data.get("space_object_graph") or {}
            ),
            space_relation_graph=SpaceRelationGraph.from_dict(
                data.get("space_relation_graph") or {}
            ),
        )
