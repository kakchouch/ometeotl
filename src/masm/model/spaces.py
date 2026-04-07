"""
This module defines the Space class, which represents a container-like context
of existence in the model.

A Space may represent a physical location, a virtual environment, or any other
contextual domain in which actors, resources, perceptions, and objectives can
exist and interact.

This module also defines:
- SpaceObjectMembership, for explicit object-to-space membership relations
- SpaceObjectGraph, for managing collections of spaces and object memberships

Warning:
Space-to-space relations are managed separately through the space_relations module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterable, Mapping

from .objects import GenericObject

JsonMap = Dict[str, Any]
ObjectId = str


def _default_schema_version() -> str:
    return "1.0"


@dataclass
class Space(GenericObject):
    """A space is a container for objects and relations. It can represent a
    physical location, a virtual environment, or any other context in which
    actors, resources, perceptions, and objectives can exist and interact.
    The Space class extends GenericObject to include specific attributes and
    relations relevant to spaces.
    It can be used to model various types of spaces, such as rooms, buildings,
    outdoor areas, digital platforms, or conceptual spaces.
    """

    object_type: str = "space"

    def __post_init__(self) -> None:
        if self.object_type != "space":
            self.object_type = "space"
        self.attributes.setdefault("kind", "abstract")
        self.attributes.setdefault("tags", [])
        self.attributes.setdefault("dimensions", {})
        self.attributes.setdefault("validity", {})

    @property
    def kind(self) -> str:
        """Get the kind of the space. The kind can be used to specify the nature
        or category of the space, such as 'physical', 'virtual', 'conceptual',
        etc."""
        value = self.attributes.get("kind", "abstract")
        return value

    @kind.setter
    def kind(self, value: str) -> None:
        """Set the kind of the space.
        The kind can be used to specify the nature or category of the space,
        such as 'physical', 'virtual', 'conceptual', etc."""
        if not value:
            raise ValueError("Kind cannot be empty")
        self.attributes["kind"] = str(value)

    @property
    def tags(self) -> List[str]:
        """Get the list of tags associated with the space.
        Tags are simple labels that can be used to categorize or describe the
        space in a flexible way.
        """
        value = self.attributes.get("tags", [])
        return sorted(list(value)) if value is not None else []

    def add_tag(self, tag: str) -> None:
        """Add a tag to the space."""
        self.add_to_attribute_list("tags", tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the space."""
        self.remove_from_attribute_list("tags", tag)

    @property
    def dimensions(self) -> JsonMap:
        """Get the dimensions of the space. Dimensions can represent
        various measurable aspects of the space,
        such as coordinates, symbolic axes, categories or other relevant
        structures describing the space.
        """
        value = self.attributes.get("dimensions", {})
        return dict(value) if isinstance(value, Mapping) else {}

    def set_dimension(self, name: str, value: Any) -> None:
        """Set a dimension for the space."""
        if not name:
            raise ValueError("Dimension name cannot be empty")
        dimensions = self.dimensions
        dimensions[name] = value
        self.attributes["dimensions"] = dict(sorted(dimensions.items()))

    @property
    def validity(self) -> JsonMap:
        """Get the validity period for the space."""
        value = self.attributes.get("validity", {})
        return dict(value) if isinstance(value, Mapping) else {}

    def set_validity(
        self, start: Optional[Any] = None, end: Optional[Any] = None
    ) -> None:
        """Set the validity period for the space."""
        validity: JsonMap = {}
        if start is not None:
            validity["start"] = start
        if end is not None:
            validity["end"] = end
        self.attributes["validity"] = validity

    def add_member(self, object_id: ObjectId) -> None:
        """DEPRECATED: Add a member to the space."""
        raise NotImplementedError(
            "Local memberships are disabled. Membership relations should be"
            " managed through SpaceObjectGraph and SpaceObjectMembership"
            " classes"
        )

    def remove_member(self, object_id: ObjectId) -> None:
        """DEPRECATED: Remove a member from the space."""
        raise NotImplementedError(
            "Local memberships are disabled. Membership relations should be"
            " managed through SpaceObjectGraph and SpaceObjectMembership"
            " classes"
        )

    def connect_to(
        self, other_space_id: ObjectId, relation: str = "adjacent_to"
    ) -> None:
        """DEPRECATED: Create a relation from this space to another space."""
        raise NotImplementedError(
            "Local space relations are disabled. Space relations should be"
            " managed through the space_relations module"
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Space":
        """Create a Space instance from a dictionary representation."""
        return cls(
            id=str(data["id"]),
            object_type=str(data.get("object_type", "space")),
            schema_version=str(data.get("schema_version", _default_schema_version())),
            attributes=dict(data.get("attributes", {})),
            relations={
                str(key): [str(item) for item in value]
                for key, value in dict(data.get("relations", {})).items()
            },
            state=dict(data.get("state", {})),
            context=dict(data.get("context", {})),
            provenance=dict(data.get("provenance", {})),
        )


@dataclass
class SpaceObjectMembership:
    """Explicit canonical relation binding a generic object to a space.
    Warning : relations between spaces are managed through the space_relations module.
    """

    object_id: ObjectId
    space_id: ObjectId
    role: str = "occupies"
    validity: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def to_dict(self) -> JsonMap:
        """Convert the SpaceObjectMembership instance to a dictionary representation."""
        return {
            "object_id": self.object_id,
            "space_id": self.space_id,
            "role": self.role,
            "validity": dict(sorted(self.validity.items())),
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpaceObjectMembership":
        """Create a SpaceObjectMembership instance from a dictionary representation."""
        return cls(
            object_id=str(data["object_id"]),
            space_id=str(data["space_id"]),
            role=str(data.get("role", "occupies")),
            validity=dict(data.get("validity", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class SpaceObjectGraph:
    """Minimal graph structure to represent spaces and their relations with objects."""

    spaces: Dict[ObjectId, Space] = field(default_factory=dict)
    object_memberships: List[SpaceObjectMembership] = field(default_factory=list)

    def add_space(self, space: Space) -> None:
        """Add a space to the graph, ensuring no duplicate IDs."""
        if space.id in self.spaces:
            raise ValueError(f"Space with id {space.id} already exists in the graph")
        self.spaces[space.id] = space

    def get_space(self, space_id: ObjectId) -> Optional[Space]:
        """Retrieve a space by its ID, or return None if it does not exist."""
        return self.spaces.get(space_id)

    def add_object_membership(self, object_membership: SpaceObjectMembership) -> None:
        """Add an object membership relation and update the corresponding space."""

        if object_membership.space_id not in self.spaces:
            raise ValueError(
                f"Space with id {object_membership.space_id} does not exist in the graph"
            )

        duplicate = any(
            existing.object_id == object_membership.object_id
            and existing.space_id == object_membership.space_id
            and existing.role == object_membership.role
            for existing in self.object_memberships
        )
        if not duplicate:
            self.object_memberships.append(object_membership)
            self.object_memberships.sort(
                key=lambda item: (item.space_id, item.object_id, item.role)
            )

    def remove_object_membership(
        self, object_membership: SpaceObjectMembership
    ) -> None:
        """Remove a membership relation and update the corresponding space."""
        self.object_memberships = [
            existing
            for existing in self.object_memberships
            if not (
                existing.object_id == object_membership.object_id
                and existing.space_id == object_membership.space_id
                and existing.role == object_membership.role
            )
        ]

    def spaces_where_object_exists(self, object_id: ObjectId) -> List[Space]:
        """Find spaces where a given object ID exists based on objectmemberships."""

        space_ids = [
            object_membership.space_id
            for object_membership in self.object_memberships
            if object_membership.object_id == object_id
        ]
        return [
            self.spaces[space_id]
            for space_id in sorted(set(space_ids))
            if space_id in self.spaces
        ]

    def shared_spaces_ids_for_objects(
        self, leftobject_id: ObjectId, rightobject_id: ObjectId
    ) -> List[ObjectId]:
        """Find shared space IDs for two given object IDs."""
        left_space_ids = {
            m.space_id for m in self.object_memberships if m.object_id == leftobject_id
        }
        right_space_ids = {
            m.space_id for m in self.object_memberships if m.object_id == rightobject_id
        }
        return sorted(left_space_ids & right_space_ids)

    def list_objects_in_space(self, space_id: ObjectId) -> List[ObjectId]:
        """List object IDs that are members of a given space ID."""
        return sorted(
            object_membership.object_id
            for object_membership in self.object_memberships
            if object_membership.space_id == space_id
        )

    def to_dict(self) -> JsonMap:
        """Convert the SpaceObjectGraph instance to a dictionary representation."""
        return {
            "spaces": {
                space_id: space.to_dict()
                for space_id, space in sorted(self.spaces.items())
            },
            "object_memberships": [
                object_membership.to_dict()
                for object_membership in sorted(
                    self.object_memberships,
                    key=lambda m: (m.space_id, m.object_id, m.role),
                )
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpaceObjectGraph":
        """Create a SpaceObjectGraph instance from a dictionary representation."""
        graph = cls()
        for space_data in data.get("spaces", {}).items():
            graph.add_space(Space.from_dict(space_data))
        for object_membership_data in data.get("object_memberships", []):
            graph.add_object_membership(
                SpaceObjectMembership.from_dict(object_membership_data)
            )
        return graph


def build_space_object_graph(
    spaces: Iterable[Space], object_memberships: Iterable[SpaceObjectMembership]
) -> SpaceObjectGraph:
    """Utility function to build a SpaceObjectGraph in a single operation."""
    graph = SpaceObjectGraph()
    for space in spaces:
        graph.add_space(space)
    for membership in object_memberships:
        graph.add_object_membership(membership)
    return graph
