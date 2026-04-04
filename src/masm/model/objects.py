from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .base import ModelObject


@dataclass
class GenericObject(ModelObject):
    """Generic representable entity in the model.

    This class is intentionally lightweight. It provides a first semantic
    layer above ModelObject before introducing more specialized domain
    objects such as actors, resources, or spaces.
    """

    @property
    def label(self) -> Optional[str]:
        value = self.attributes.get("label")
        return str(value) if value is not None else None

    @label.setter
    def label(self, value: str) -> None:
        if not value:
            raise ValueError("Label cannot be empty")
        self.attributes["label"] = value

    @property
    def description(self) -> Optional[str]:
        value = self.attributes.get("description")
        return str(value) if value is not None else None

    @description.setter
    def description(self, value: str) -> None:
        if not value:
            raise ValueError("Description cannot be empty")
        self.attributes["description"] = value