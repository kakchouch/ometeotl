"""
This module defines explicit relations between spaces.

Supported relation families include:
- adjacency (e.g. "adjacent_to")
- containment / hierarchy (e.g. "contains_space")
- intersection / overlap (e.g. "intersects_with")

Warning:
This module manages only space-to-space relations.
Object-to-space memberships are managed separately in spaces.py.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Any

SpaceId = str
JsonMap = Dict[str, Any]


@dataclass(frozen=True)
class SpaceRelationType:
    """Defines the types of relations that can exist between spaces."""

    name: str  # e.g. "adjacent_to", "contains_space", "intersects_with", etc.
    is_symmetric: bool = (
        False  # Whether the relation is symmetric (e.g. "adjacent_to" is
        # symmetric, "contains_space" is not)
    )
    is_antisymmetric: bool = (
        False  # Whether the relation is antisymmetric (e.g. "contains_space"
        # is antisymmetric, "adjacent_to" is not)
    )
    is_transitive: bool = (
        False  # Whether the relation is transitive (e.g. "contains_space" is
        # transitive, "adjacent_to" is not)
    )
    is_reflexive: bool = (
        False  # Whether the relation is reflexive (e.g. "contains_space" is
        # reflexive, "adjacent_to" is not)
    )


SPACE_RELATION_TYPES: Dict[str, SpaceRelationType] = {
    "adjacent_to": SpaceRelationType(
        name="adjacent_to",
        is_symmetric=True,
        is_antisymmetric=False,
        is_transitive=False,
        is_reflexive=False,
    ),
    "contains_space": SpaceRelationType(
        name="contains_space",
        is_transitive=True,
        is_reflexive=False,
        is_antisymmetric=True,
    ),  # Convention: Self-reflexivity is not allowed for "contains_space"
    # to avoid paradoxes and maintain a clear hierarchy of spaces.
    "intersects_with": SpaceRelationType(
        name="intersects_with",
        is_symmetric=True,
        is_antisymmetric=False,
        is_transitive=False,
        is_reflexive=False,
    ),
}


@dataclass(frozen=True)
class SpaceRelation:
    """Represents a relation between two spaces.

    Examples:
    - adjacency ("adjacent_to")
    - containment / hierarchy ("contains_space")
    - intersection ("intersects_with")

    Warning:
    This class manages only space-to-space relations.
    Object-to-space memberships are handled through SpaceObjectMembership
    and SpaceObjectGraph in spaces.py.
    """

    source_space_id: SpaceId
    target_space_id: SpaceId
    relation_type: str  # e.g. "adjacent_to", "contains", etc.
    metadata: JsonMap = field(default_factory=dict)

    def canonicalize(self) -> SpaceRelation:
        """Return a canonicalized version of the relation, where symmetric
        relations are ordered by space IDs."""
        relation_def = SPACE_RELATION_TYPES.get(self.relation_type)
        if relation_def is None:
            return self  # If the relation type is unknown, return as is
            # without canonicalization
        if relation_def.is_symmetric and self.source_space_id > self.target_space_id:
            return SpaceRelation(
                source_space_id=self.target_space_id,
                target_space_id=self.source_space_id,
                relation_type=self.relation_type,
                metadata=dict(self.metadata),
            )
        return self

    def to_dict(self) -> JsonMap:
        """Convert the SpaceRelation instance to a dictionary representation."""
        return {
            "source_space_id": self.source_space_id,
            "target_space_id": self.target_space_id,
            "relation_type": self.relation_type,
            "metadata": dict(sorted(self.metadata.items())),
        }

    def __deepcopy__(self, memo: dict) -> "SpaceRelation":
        """Optimised deep copy: immutable str fields are shared; only
        the mutable metadata dict is deep-copied."""
        cls = self.__class__
        new_obj: SpaceRelation = cls.__new__(cls)
        memo[id(self)] = new_obj
        for f in dataclasses.fields(self):
            object.__setattr__(
                new_obj, f.name, copy.deepcopy(getattr(self, f.name), memo)
            )
        return new_obj

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpaceRelation":
        """Create a SpaceRelation instance from a dictionary representation."""
        if data.get("source_space_id") is None:
            raise ValueError("Field 'source_space_id' cannot be null")
        if data.get("target_space_id") is None:
            raise ValueError("Field 'target_space_id' cannot be null")
        if data.get("relation_type") is None:
            raise ValueError("Field 'relation_type' cannot be null")
        return cls(
            source_space_id=str(data["source_space_id"]),
            target_space_id=str(data["target_space_id"]),
            relation_type=str(data["relation_type"]),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SpaceRelationGraph:
    """Represents a graph of space-to-space relations.

    Warning:
    This class manages only relations between spaces.
    Object-to-space memberships are handled separately through
    SpaceObjectMembership and SpaceObjectGraph in spaces.py.

    This separation keeps the model clearer and allows flexible
    extension of relation types between spaces.
    """

    relations: List[SpaceRelation] = field(default_factory=list)

    def add_relation(self, relation: SpaceRelation) -> None:
        """Add a relation between two spaces.

        No duplicate relations are allowed (same source, target, and relation type).
        Symmetric relations are automatically canonicalized to ensure a consistent representation.
        Antisymmetric relations are not automatically canonicalized, as direction matters.
        Self-relations are not allowed for non-reflexive relation types.
        """

        normalized_relation = relation.canonicalize()
        relation_def = SPACE_RELATION_TYPES.get(normalized_relation.relation_type)

        if relation_def is None:
            raise ValueError(
                f"Unknown relation type: {normalized_relation.relation_type}"
            )

        # Enforce self-reflexivity rules based on the relation definition
        if (
            not relation_def.is_reflexive
            and normalized_relation.source_space_id
            == normalized_relation.target_space_id
        ):
            raise ValueError(
                f"Relation of type '{normalized_relation.relation_type}' is not"
                " reflexive. Self-relations are not allowed for this relation"
                " type."
            )

        #
        if relation_def.is_antisymmetric:
            inverse_relation_exists = any(
                existing.source_space_id == normalized_relation.target_space_id
                and existing.target_space_id == normalized_relation.source_space_id
                and existing.relation_type == normalized_relation.relation_type
                and existing.source_space_id
                != existing.target_space_id  # Ensure it's not a self-reflexive relation
                for existing in self.relations
            )
            if inverse_relation_exists:
                raise ValueError(
                    f"Cannot add relation '{normalized_relation.relation_type}'"
                    f" from '{normalized_relation.source_space_id}' to"
                    f" '{normalized_relation.target_space_id}' because it would"
                    " violate antisymmetry with an existing inverse relation."
                )

        # Check for duplicates based on the canonicalized relation
        duplicate = any(existing == normalized_relation for existing in self.relations)

        if duplicate:
            return

        self.relations.append(normalized_relation)
        self.relations.sort(
            key=lambda r: (r.source_space_id, r.target_space_id, r.relation_type)
        )  # Keep relations sorted for consistency

    def remove_relation(
        self, source_space_id: SpaceId, target_space_id: SpaceId, relation_type: str
    ) -> None:
        """Remove a relation between two spaces."""
        normalized_relation = SpaceRelation(
            source_space_id=source_space_id,
            target_space_id=target_space_id,
            relation_type=relation_type,
        ).canonicalize()

        self.relations = [
            r
            for r in self.relations
            if not (
                r.source_space_id == normalized_relation.source_space_id
                and r.target_space_id == normalized_relation.target_space_id
                and r.relation_type == normalized_relation.relation_type
            )
        ]

    def relations_from(
        self, space_id: SpaceId, relation_type: Optional[str] = None
    ) -> List[SpaceRelation]:
        """Get all relations originating from a given space."""
        return [
            r
            for r in self.relations
            if r.source_space_id == space_id
            and (relation_type is None or r.relation_type == relation_type)
        ]

    def relations_to(
        self, space_id: SpaceId, relation_type: Optional[str] = None
    ) -> List[SpaceRelation]:
        """Get all relations targeting a given space."""
        return [
            r
            for r in self.relations
            if r.target_space_id == space_id
            and (relation_type is None or r.relation_type == relation_type)
        ]

    def children_of(self, space_id: SpaceId) -> List[SpaceId]:
        """Get all "contains_space" relations where the given space is the target.
        Convention : "contains_space" relations indicate that the source space
        contains the target space.
        If SRC contains TGT :
         then SRC is the parent
         and TGT is the child."""
        return sorted(
            relation.target_space_id
            for relation in self.relations_from(
                space_id, relation_type="contains_space"
            )
        )

    def parents_of(self, space_id: SpaceId) -> List[SpaceId]:
        """Get all "contains_space" relations where the given space is the source.
        Convention : "contains_space" relations indicate that the source space
        contains the target space.
        If SRC contains TGT :
         then SRC is the parent
         and TGT is the child."""
        return sorted(
            relation.source_space_id
            for relation in self.relations_to(space_id, relation_type="contains_space")
        )

    def neighbors_of(self, space_id: SpaceId) -> List[SpaceId]:
        """Get all spaces that are adjacent to the given space.
        Convention : "adjacent_to" relations indicate that the source space
        is adjacent to the target space.
        """
        outgoing_neighbors = {
            relation.target_space_id
            for relation in self.relations_from(space_id, relation_type="adjacent_to")
        }
        incoming_neighbors = {
            relation.source_space_id
            for relation in self.relations_to(space_id, relation_type="adjacent_to")
        }
        return sorted(outgoing_neighbors.union(incoming_neighbors))

    def intersects_with(self, space_id: SpaceId) -> List[SpaceId]:
        """Get all spaces that intersect with the given space.
        Convention : "intersects_with" relations indicate that the source space
        intersects with the target space.
        """
        outgoing_intersections = {
            relation.target_space_id
            for relation in self.relations_from(
                space_id, relation_type="intersects_with"
            )
        }
        incoming_intersections = {
            relation.source_space_id
            for relation in self.relations_to(space_id, relation_type="intersects_with")
        }
        return sorted(outgoing_intersections.union(incoming_intersections))

    def to_dict(self) -> JsonMap:
        """Convert the SpaceRelationGraph to a canonical dictionary representation."""
        return {
            "relations": [r.to_dict() for r in self.relations],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SpaceRelationGraph":
        """Reconstruct a SpaceRelationGraph from a canonical dictionary representation."""
        graph = cls()
        for relation_data in data.get("relations") or []:
            graph.add_relation(SpaceRelation.from_dict(relation_data))
        return graph
