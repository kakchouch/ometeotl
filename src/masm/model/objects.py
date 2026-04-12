"""Generic representable entity in the model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Optional

from .base import ModelObject, JsonMap


@dataclass
class GenericObject(ModelObject):
    """Generic representable entity in the model.

    This class is intentionally lightweight. It provides a first semantic
    layer above ModelObject before introducing more specialized domain
    objects such as actors, resources, or spaces.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.id:
            raise ValueError("Object id cannot be empty")

    @property
    def label(self) -> Optional[str]:
        """Get the object's label."""
        value = self.attributes.get("label")
        return str(value) if value is not None else None

    @label.setter
    def label(self, value: str) -> None:
        """Set the object's label."""
        if not value:
            raise ValueError("Label cannot be empty")
        self.attributes["label"] = value

    @property
    def description(self) -> Optional[str]:
        """Get the object's description."""
        value = self.attributes.get("description")
        return str(value) if value is not None else None

    @description.setter
    def description(self, value: str) -> None:
        """Set the object's description."""
        if not value:
            raise ValueError("Description cannot be empty")
        self.attributes["description"] = value

    @property
    def tags(self) -> List[str]:
        """Get the object's tags.

        Tags are simple labels used for categorization, filtering, or search.
        """
        value = self.attributes.get("tags", [])
        return sorted(list(value)) if value is not None else []

    def add_tag(self, tag: str) -> None:
        """Add a tag to the object."""
        self.add_to_attribute_list("tags", tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the object."""
        self.remove_from_attribute_list("tags", tag)

    @property
    def profile(self) -> JsonMap:
        """Get the object's free-form profile.

        Structured data capturing specific characteristics or attributes of
        the object in a detailed and organized way. Intentionally open-ended.
        """
        value = self.attributes.get("profile", {})
        return dict(value) if isinstance(value, Mapping) else {}

    def set_profile_item(self, key: str, value: Any) -> None:
        """Set a specific item in the object's profile."""
        if not key:
            raise ValueError("Profile key cannot be empty")
        profile = dict(self.profile)
        profile[key] = value
        self.attributes["profile"] = dict(sorted(profile.items()))
