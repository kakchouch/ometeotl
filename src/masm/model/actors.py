"""Actor model primitives.

This module contains the Actor class, which represents an actor in the model.

An actor is an abstract entity existing in one or several spaces of
existence, time being one of them. It may be characterized by:
- one or several spaces in which it exists;
- a set of attributes (for example a name);
- a set of actions it can perform;
- a set of resources it can use, which constrain the actions it can perform;
- a set of values from which it may derive utility, preferences, and goals;
- a set of goals it seeks to achieve;
- a set of constraints and limitations it is subject to.

Actors can take different forms, such as individuals, groups,
organizations, institutions, or other composite entities. An actor may
emerge from the perceptions of other actors, for example as a loose
collection of entities perceived as a coherent whole, or may correspond
to a more concrete and organized entity such as a company or a country.

Actors may also be treated as resources by other actors depending on the
modeling context, and may themselves be composed of other actors.

Due to the possible emergent complexity of actors, this class is designed
to remain flexible and extensible, allowing additional attributes,
relations, and modeling conventions to be introduced progressively.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from .base import relation_methods
from .objects import GenericObject
from .spaces import SpaceObjectGraph, SpaceObjectMembership

# local aliases
JsonMap = Dict[str, Any]
ObjectId = str


def _default_schema_version() -> str:
    return "1.0"


@relation_methods("action", "action")
@relation_methods("resource", "resource")
@relation_methods("value", "value")
@relation_methods("goal", "goal")
@relation_methods("constraint", "constraint")
@relation_methods("component", "component")
@relation_methods("membership", "membership")
@relation_methods("dependency", "dependency")
@relation_methods("cooperation", "cooperation")
@relation_methods("conflict", "conflict")
@dataclass
class Actor(GenericObject):
    """Represents an actor in the model.
    Actors can represent individuals, groups, organizations, institutions,
    states, or emergent entities. They may also be composed of other actors
    and may themselves be treated as resources depending on the modeling
    context.

    This class is intentionally lightweight and extensible:
    - intrinsic descriptive data is stored in ``attributes``;
    - links to other model objects are stored in ``relations``;
    - dynamic evolution remains possible through ``state`` and ``context``."""

    object_type: str = "actor"

    def __post_init__(self) -> None:
        """Normalize and initialize actors default values."""
        super().__post_init__()
        if self.object_type != "actor":
            self.object_type = "actor"

        self.attributes.setdefault("kind", "generic")
        self.attributes.setdefault("tags", [])
        self.attributes.setdefault("roles", [])
        self.attributes.setdefault("profiles", {})
        self.attributes.setdefault("emergent", False)
        self.attributes.setdefault("composition_mode", "standalone")

    @property
    def kind(self) -> str:
        """Returns the actor's, kind.
        Typical examples include :
        -"individual": a single person or entity;
        -"group": a collection of individuals or entities;
        -organization: a structured group with specific roles and functions;
        -emergent: a loosely defined entity emerging from the perceptions of other actors.
        """

        value = self.attributes.get("kind", "generic")
        return str(value) if value is not None else "generic"

    @kind.setter
    def kind(self, value: str) -> None:
        """Sets the actor's kind."""
        if not value:
            raise ValueError("Kind cannot be empty")
        self.attributes["kind"] = value

    @property
    def tags(self) -> List[str]:
        """Return the actor's tags.

        Tags are simple labels that can be used for categorization,
        filtering, or search.
        """
        value = self.attributes.get("tags", [])
        return sorted(list(value)) if value is not None else []

    def add_tag(self, tag: str) -> None:
        """Adds a tag to the actor."""
        self.add_to_attribute_list("tags", tag)

    def remove_tag(self, tag: str) -> None:
        """Removes a tag from the actor."""
        self.remove_from_attribute_list("tags", tag)

    @property
    def roles(self) -> List[str]:
        """Return the actor's roles.

        Roles are specific functions or positions that the actor can assume
        within a particular context or interaction.
        """
        roles = self.attributes.get("roles", [])
        return sorted(list(roles)) if roles is not None else []

    def add_role(self, role: str) -> None:
        """Adds a role to the actor."""
        self.add_to_attribute_list("roles", role)

    def remove_role(self, role: str) -> None:
        """Removes a role from the actor."""
        self.remove_from_attribute_list("roles", role)

    @property
    def profile(self) -> JsonMap:
        """Return the actor's free-form profile.

        Structured data that can be used to capture specific characteristics,
        preferences, or attributes of the actor in a more detailed and
        organized way. This dictionary is intentionally open-ended and can
        contain modeling details such as category-specific metadata,
        identifiers, demographic information etc.
        """
        value = self.attributes.get("profile", {})
        return dict(value) if isinstance(value, Mapping) else {}

    def set_profile_item(self, key: str, value: Any) -> None:
        """Sets a specific item in the actor's profile."""
        if not key:
            raise ValueError("Profile key cannot be empty")
        profile = self.profile
        profile[key] = value
        self.attributes["profile"] = dict(sorted(profile.items()))

    @property
    def emergent(self) -> bool:
        """Returns whether the actor is emergent, meaning it is a loosely
        defined entity emerging from the perceptions of other actors."""
        value = self.attributes.get("emergent", False)
        return bool(value)

    @emergent.setter
    def emergent(self, value: bool) -> None:
        """Sets whether the actor is emergent."""
        self.attributes["emergent"] = bool(value)

    @property
    def composition_mode(self) -> str:
        """Returns the actor's composition mode, which indicates how the actor
        is composed of other actors if it is a composite entity.
        Typical values include:
        - "standalone": the actor is not composed of other actors;
        - "composite": the actor is composed of other actors, which are
          explicitly linked to it through relations;
        - "collective": the actor is a loosely defined collection of other
          actors, which are not explicitly linked to it but are perceived as
          a coherent whole.
        - "perceived": the actor is an emergent entity perceived by other
          actors as a coherent whole, without a clear internal structure or
          composition.
        - "projected": the actor is a projected entity that may not have a
          clear existence but is treated as an actor for modeling purposes or
          through other actors interactions.
        """
        value = self.attributes.get("composition_mode", "standalone")
        return str(value) if value is not None else "standalone"

    @composition_mode.setter
    def composition_mode(self, value: str) -> None:
        """Sets the actor's composition mode."""
        if not value:
            raise ValueError("Composition mode cannot be empty")
        self.attributes["composition_mode"] = value

    # ------------------------------------------------------------------
    # Domain relations
    # ------------------------------------------------------------------
    # Important idea:
    # In this architecture, actions, resources, goals etc. are not stored as
    # complex objects directly in the actor, but rather as relations to other
    # model objects. This allows for greater flexibility and extensibility,
    # as well as a clearer separation of concerns. It ensures fidelity with
    # ModelObject.relations, which is the canonical place for storing links
    # between model objects.

    def add_space_membership(
        self,
        graph: "SpaceObjectGraph",
        space_id: ObjectId,
        role: str = "occupies",
        *,
        validity: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Declare that this actor exists in a given space.

        Important:
        This is a convenience wrapper. Canonical object-to-space memberships
        are stored in SpaceObjectMembership objects managed by SpaceObjectGraph.
        """

        graph.add_object_membership(
            SpaceObjectMembership(
                object_id=self.id,
                space_id=space_id,
                role=role,
                validity=dict(validity or {}),
                metadata=dict(metadata or {}),
            )
        )

    def remove_space_membership(
        self, graph: "SpaceObjectGraph", space_id: ObjectId, role
    ) -> None:
        """Remove the declaration that this resource exists in a given space.

        Important:
        This method is only a convenience wrapper around SpaceObjectMembership
        and SpaceObjectGraph. The canonical membership data is stored in the graph.
        """

        graph.remove_object_membership(
            SpaceObjectMembership(
                object_id=self.id,
                space_id=space_id,
                role=role,
            )
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Actor":
        """Create an Actor instance from a dictionary representation."""
        return cls(
            id=str(data["id"]),
            object_type=str(data.get("object_type", "actor")),
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

    def to_dict(self) -> JsonMap:
        """Convert the Actor instance to a dictionary representation."""
        return {
            "id": self.id,
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "attributes": dict(self.attributes),
            "relations": {
                key: sorted(list(set(value)))
                for key, value in dict(self.relations).items()
            },
            "state": dict(self.state),
            "context": dict(self.context),
            "provenance": dict(self.provenance),
        }
