"""
This module defines the Space class, which represents a container for objects and relations in the model. I
It is abstract, and may represent physical locations, virtual environments, or any other context in which actors, resources,
 perceptions, and objectives can exist and interact. 
Spaces may have an internal hierarchy of subspaces, and can be connected to other spaces through various relations. 
 The module also defines the SpaceObjectMembership class for explicit relations between objects and spaces,
 Warning : relations between spaces are managed through the space_relations module.
  and the SpaceGraph class for managing collections of spaces and their memberships.
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
    """A space is a container for objects and relations. It can represent a physical location, a virtual environment,
     or any other context in which actors, resources, perceptions, and objectives can exist and interact.
    The Space class extends GenericObject to include specific attributes and relations relevant to spaces. 
    It can be used to model various types of spaces, such as rooms, buildings, outdoor areas, digital platforms, or conceptual spaces.
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
        """Get the kind of the space. The kind can be used to specify the nature or category of the space, such as 'physical', 'virtual', 'conceptual', etc."""
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
        Tags are simple labels that can be used to categorize or describe the space in a flexible way."""
        raw_tags = self.attributes.get("tags", [])
        return [str(item) for item in raw_tags]

    def add_tag(self, tag: str) -> None:
        """Add a tag to the space."""
        if not tag:
            raise ValueError("Tag cannot be empty")
        tags = self.tags
        if tag not in tags:
            tags.append(tag)
        self.attributes["tags"] = sorted(tags)

    @property
    def dimensions(self) -> JsonMap:
        """Get the dimensions of the space. Dimensions can represent 
        various measurable aspects of the space, 
        such as coordinates, symbolic axes, categories or other relevant structures describing the space."""
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

    def set_validity(self, start: Optional[Any] = None, end: Optional[Any] = None) -> None:
        """Set the validity period for the space."""
        validity: JsonMap = {}
        if start is not None:
            validity["start"] = start
        if end is not None:
            validity["end"] = end
        self.attributes["validity"] = validity

    def add_member(self, object_id: ObjectId) -> None:
        """Add a member to the space."""
        raise NotImplementedError("Local memberships are disabled.Membership relations should be managed through SpaceGraph and SpaceObjectMembership classes")

    def remove_member(self, object_id: ObjectId) -> None:
        """Remove a member from the space."""
        raise NotImplementedError("Local memberships are disabled.Membership relations should be managed through SpaceGraph and SpaceObjectMembership classes")

    def connect_to(self, other_space_id: ObjectId, relation: str = "adjacent_to") -> None:
        """Create a relation from this space to another space."""
        self.add_relation(relation, other_space_id)

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
    """Explicit canonical relation binding an generic object to a space. 
    Warning : relations between spaces are managed through the space_relations module."""

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
    def from_dict(cls, data: Mapping[str, Any]) -> "SpaceMembership":
        """Create a SpaceObjectMembership instance from a dictionary representation."""
        return cls(
            object_id=str(data["object_id"]),
            space_id=str(data["space_id"]),
            role=str(data.get("role", "occupies")),
            validity=dict(data.get("validity", {})),
            metadata=dict(data.get("metadata", {})),
        )



@dataclass
class SpaceGraph:
    """Minimal graph structure to represent spaces and their relations,
     including memberships."""

    spaces: Dict[ObjectId, Space] = field(default_factory=dict)
    memberships: List[SpaceObjectMembership] = field(default_factory=list)

    def add_space(self, space: Space) -> None:
        """Add a space to the graph, ensuring no duplicate IDs."""
        if  space.id in self.spaces:
            raise ValueError(f"Space with id {space.id} already exists in the graph")
        self.spaces[space.id] = space

    def get_space(self, space_id: ObjectId) -> Optional[Space]:
        """Retrieve a space by its ID, or return None if it does not exist."""
        return self.spaces.get(space_id)

    def add_membership(self, membership: SpaceObjectMembership) -> None:
        """Add a membership relation and update the corresponding space."""
   
        if membership.space_id not in self.spaces:
            raise ValueError(f"Space with id {membership.space_id} does not exist in the graph")
        

        duplicate = any(
            existing.object_id == membership.object_id 
            and existing.space_id == membership.space_id
            and existing.role == membership.role
            for existing in self.memberships
        )
        if not duplicate:
            self.memberships.append(membership)
            self.memberships.sort(key=lambda item: (item.space_id, item.object_id, item.role))

    def remove_membership(self, membership: SpaceObjectMembership) -> None:
        """Remove a membership relation and update the corresponding space."""
        self.memberships = [
            existing for existing in self.memberships
            if not (
                existing.object_id == membership.object_id 
                and existing.space_id == membership.space_id
                and existing.role == membership.role
            )
        ]


    def spaces_where_object_exists(self, object_id: ObjectId) -> List[Space]:
        """Find spaces where a given object ID exists based on memberships."""

        space_ids = [
            membership.space_id for membership in self.memberships
            if membership.object_id == object_id
        ]
        return [self.spaces[space_id] for space_id in sorted(set(space_ids)) if space_id in self.spaces]

    def shared_spaces_ids_for_objects(self, leftobject_id: ObjectId, rightobject_id: ObjectId) -> List[ObjectId]:
        """Find shared space IDs for two given object IDs."""
        left_space_ids = {m.space_id for m in self.memberships if m.object_id == leftobject_id}
        right_space_ids = {m.space_id for m in self.memberships if m.object_id == rightobject_id}
        return sorted(left_space_ids & right_space_ids)

    def list_objects_in_space(self, space_id: ObjectId) -> List[ObjectId]:
        """List object IDs that are members of a given space ID."""
        return sorted(
            membership.object_id for membership in self.memberships
            if membership.space_id == space_id
        )
    
    def to_dict(self) -> JsonMap:
        """Convert the SpaceGraph instance to a dictionary representation."""
        return {
            "spaces": {space_id: space.to_dict() for space_id, space in sorted(self.spaces.items())},
            "memberships": [membership.to_dict() for membership in sorted(self.memberships, key=lambda m: (m.space_id, m.object_id, m.role))],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpaceGraph":
        """Create a SpaceGraph instance from a dictionary representation."""
        graph = cls()
        for space_id, space_data in data.get("spaces", {}).items():
            graph.add_space(Space.from_dict(space_data))
        for membership_data in data.get("memberships", []):
            graph.add_membership(SpaceObjectMembership.from_dict(membership_data))
        return graph


def build_space_graph(spaces: Iterable[Space], memberships: Iterable[SpaceObjectMembership]) -> SpaceGraph:
    """Utility function to build a SpaceGraph in a single operation."""
    graph = SpaceGraph()
    for space in spaces:
        graph.add_space(space)
    for membership in memberships:
        graph.add_membership(membership)
    return graph