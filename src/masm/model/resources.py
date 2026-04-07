"""Resource model primitives.

This module defines the Resource class, which represents a resource in the model.

Resources are a specific type of objects that may be placed at the disposal of
actors. They exist in their own spaces of existence, which can be shared with
actors, objects, or other resources.

Such spaces can be directly linked to other spaces, or connected indirectly
through other objects or actors.

Semantically, resources can represent anything that actors can use to perform
actions, such as tools, materials, energy, human resources, or symbolic resources.

However, Resource is an abstract type inherited from GenericObject, and it should
not be used directly by the user to implement specific resources for their
intended business logic.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Dict, Mapping

from .base import relation_methods
from .objects import GenericObject
from .spaces import SpaceObjectGraph, SpaceObjectMembership

# local aliases
JsonMap = Dict[str, Any]
ObjectId = str


def _default_schema_version() -> str:
    return "1.0"


@relation_methods("user", "used_by")
@relation_methods("controller", "controlled_by")
@relation_methods("owner", "owned_by")
@relation_methods("dependency", "depends_on")
@relation_methods("component", "has_component")
@dataclass
class Resource(GenericObject):
    """A resource in the model.

    Resources are a specific type of objects that may be placed at the disposal of
    actors. They exist in their own spaces of existence, which can be shared with
    actors, objects, or other resources.

    Such spaces can be directly linked to other spaces, or connected indirectly
    through other objects or actors.

    Semantically, resources can represent anything that actors can use to perform
    actions, such as tools, materials, energy, human resources, or symbolic resources.
    """

    object_type: str = "resource"

    def __post_init__(self) -> None:
        if self.object_type != "resource":
            self.object_type = "resource"

        self.attributes.setdefault("kind", "generic")
        # generic attributes inherited from the Resource class, which can be
        # used to classify resources into different types or categories
        # (e.g., "material", "energy", "human", "symbolic", etc.)
        self.attributes.setdefault("tags", [])
        # a list of tags that can be used to label and categorize the resource
        # for easier searching and filtering (e.g., "renewable", "non-renewable",
        # "scarce", "abundant", etc.)
        self.attributes.setdefault("resource_mode", "stock")
        # is the resource a stock (accumulates over time) or a flow
        # (instantaneous), a capacity, an access point, etc.?
        self.attributes.setdefault("rivalry", "mixed")
        # is the resource rivalrous (consumption by one actor reduces
        # availability for others), non-rivalrous (consumption by one actor
        # does not affect availability for others), or mixed (some aspects are
        # rivalrous and others are non-rivalrous)?
        self.attributes.setdefault("transferability", "mixed")
        # is the resource transferable (can be transferred between actors),
        # non-transferable (cannot be transferred between actors), or mixed
        # (some aspects are transferable and others are non-transferable)?
        self.attributes.setdefault("divisibility", "mixed")
        # is the resource divisible (can be divided into smaller units),
        # indivisible (cannot be divided into smaller units), or mixed (some
        # aspects are divisible and others are indivisible)?
        self.attributes.setdefault("composite", False)
        # is the resource composite (made up of multiple components or
        # sub-resources) or simple (not made up of multiple components or
        # sub-resources)?
        self.attributes.setdefault("profile", {})
        # a dictionary that can be used to store additional information about
        # the resource, such as its properties, characteristics, or
        # specifications (e.g., for a material resource, this could include
        # its density, melting point, etc.)

    @property
    def kind(self) -> str:
        """The kind of resource."""
        value = self.attributes.get("kind", "generic")
        return str(value) if value is not None else "generic"

    @kind.setter
    def kind(self, value: str) -> None:
        """Set the kind of resource."""
        if not value:
            raise ValueError("Kind cannot be empty.")
        self.attributes["kind"] = str(value)

    @property
    def tags(self) -> List[str]:
        """The tags of the resource."""
        value = self.attributes.get("tags", [])
        return sorted(list(value)) if value is not None else []

    def add_tag(self, tag: str) -> None:
        """Add a tag to the resource."""
        self.add_to_attribute_list("tags", tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the resource."""
        self.remove_from_attribute_list("tags", tag)

    @property
    def resource_mode(self) -> str:
        """The resource mode of the resource."""
        value = self.attributes.get("resource_mode", "stock")
        return str(value) if value is not None else "stock"

    @resource_mode.setter
    def resource_mode(self, value: str) -> None:
        """Set the resource mode of the resource."""
        if not value:
            raise ValueError("Resource mode cannot be empty.")
        self.attributes["resource_mode"] = str(value)

    @property
    def rivalry(self) -> str:
        """The rivalry regime of the resource."""
        value = self.attributes.get("rivalry", "mixed")
        return str(value) if value is not None else "mixed"

    @rivalry.setter
    def rivalry(self, value: str) -> None:
        """Set the rivalry of the resource."""
        if not value:
            raise ValueError("Rivalry cannot be empty.")
        self.attributes["rivalry"] = str(value)

    @property
    def transferability(self) -> str:
        """The transferability of the resource."""
        value = self.attributes.get("transferability", "mixed")
        return str(value) if value is not None else "mixed"

    @transferability.setter
    def transferability(self, value: str) -> None:
        """Set the transferability of the resource."""
        if not value:
            raise ValueError("Transferability cannot be empty.")
        self.attributes["transferability"] = str(value)

    @property
    def divisibility(self) -> str:
        """The divisibility of the resource."""
        value = self.attributes.get("divisibility", "mixed")
        return str(value) if value is not None else "mixed"

    @divisibility.setter
    def divisibility(self, value: str) -> None:
        """Set the divisibility of the resource."""
        if not value:
            raise ValueError("Divisibility cannot be empty")
        self.attributes["divisibility"] = str(value)

    @property
    def composite(self) -> bool:
        """Whether the resource is composite."""
        value = self.attributes.get("composite", False)
        return bool(value) if value is not None else False

    @composite.setter
    def composite(self, value: bool) -> None:
        """Set whether the resource is composite."""
        self.attributes["composite"] = bool(value)

    @property
    def profile(self) -> JsonMap:
        """Returns the free-form profile of the resource, which are structured
        data that can be used to capture specific characteristics, preferences,
        or attributes of the resource in a more detailed and organized way.
        This dictionnary is intentionally open-ended and can contain
        modeling details such as category-specific metadata,
        identifiers etc."""
        value = self.attributes.get("profile", {})
        return dict(value) if isinstance(value, Mapping) else {}

    def set_profile_item(self, key: str, value: Any) -> None:
        """Sets a specific item in the resource's profile."""
        if not key:
            raise ValueError("Profile key cannot be empty")
        profile = self.profile
        profile[key] = value
        self.attributes["profile"] = dict(sorted(profile.items()))

    # ------------------------------------------------------------------
    # Domain relations
    # ------------------------------------------------------------------
    # Important idea :
    # In this architecture, ownership, usage, dependency and other
    # relationships are not stored as complex objects directly in the
    # resource, but rather as relations to other model objects.
    # This allows for greater flexibility and extensibility, as well as a
    # clearer separation of concerns.
    # It ensures fidelity with  ModelObject.relations, which is the
    # canonical place for storing links between model objects.

    def add_space_membership(
        self,
        graph: "SpaceObjectGraph",
        space_id: ObjectId,
        role: str = "occupies",
        *,
        validity: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Declare that this resource exists in a given space.

        Important:
        This method is only a convenience wrapper around SpaceObjectMembership
        and SpaceObjectGraph. The canonical membership data is stored in the graph.
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
        self, graph: "SpaceObjectGraph", space_id: ObjectId, role: str = "occupies"
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
    def from_dict(cls, data: Mapping[str, Any]) -> "Resource":
        """Create the resource from a dictionary."""
        return cls(
            id=str(data["id"]),
            object_type=str(data.get("object_type", "resource")),
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
