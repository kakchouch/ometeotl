"""Base model object class for all objects in the Ometeotl/MASM framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

# NEW: Decorator for auto-generating add/remove methods
def relation_methods(method_name: str, rel_name: str):
    """Decorator to generate add/remove pairs."""
    def decorator(cls):
        def add_method(self, target_id: ObjectId) -> None:
            self._manage_relation(rel_name, target_id, add=True)
        
        def remove_method(self, target_id: ObjectId) -> None:
            self._manage_relation(rel_name, target_id, add=False)
        
        add_method.__name__ = f"add_{method_name}"
        remove_method.__name__ = f"remove_{method_name}"
        add_method.__doc__ = f"Adds {method_name} relation."
        remove_method.__doc__ = f"Removes {method_name} relation."
        
        setattr(cls, add_method.__name__, add_method)
        setattr(cls, remove_method.__name__, remove_method)
        return cls
    return decorator

SchemaVersion = str
ObjectId = str
RelationMap = Dict[str, List[ObjectId]]
JsonMap = Dict[str, Any]


def _default_schema_version() -> str:
    return "1.0"


@dataclass
class ModelObject:
    """A base class for all objects in the model.

    It contains the common fields and methods that all objects share.
    It is voluntarily designed to be as simple as possible, and to be easily
    extendable by subclasses. It should not contain any logic that is specific
    to a particular object_type of object, but rather should be a generic
    container for data that can be used by subclasses. No specific hypothesis
    about the actors, resources, perceptions, objectifs should be included.
    """

    id: ObjectId
    object_type: str
    schema_version: SchemaVersion = field(default_factory=_default_schema_version)
    attributes: JsonMap = field(default_factory=dict)
    relations: RelationMap = field(default_factory=dict)
    state: JsonMap = field(default_factory=dict)
    context: JsonMap = field(default_factory=dict)
    provenance: JsonMap = field(default_factory=dict)

    def add_relation(self, name: str, target_id: ObjectId) -> None:
        """Add a relation to another object."""
        if not name:
            raise ValueError("Relation name cannot be empty")
        if not target_id:
            raise ValueError("Target ID cannot be empty")
        self.relations.setdefault(name, [])
        if target_id not in self.relations[name]:
            self.relations[name].append(target_id)
            self.relations[name].sort()

    def remove_relation(self, name: str, target_id: ObjectId) -> None:
        """Remove a relation to another object."""
        if name not in self.relations:
            return
        self.relations[name] = [
            existing_id
            for existing_id in self.relations[name]
            if existing_id != target_id
        ]
        if not self.relations[name]:
            del self.relations[name]

    def _manage_relation(self, rel_name: str, target_id: ObjectId, add: bool = True) -> None:
        """Generic add/remove for relations. Used by subclasses."""
        if not rel_name:
            raise ValueError("Relation name cannot be empty")
        if not target_id:
            raise ValueError("Target ID cannot be empty")
        
        if rel_name not in self.relations:
            self.relations[rel_name] = []
        
        rel_list: List[ObjectId] = self.relations[rel_name]
        if add:
            if target_id not in rel_list:
                rel_list.append(target_id)
                rel_list.sort()  # Keep sorted for determinism
        else:
            if target_id in rel_list:
                rel_list.remove(target_id)
                if not rel_list:
                    del self.relations[rel_name]

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the object."""
        if not key:
            raise ValueError("Attribute key cannot be empty")
        self.attributes[key] = value

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value on the object."""
        if not key:
            raise ValueError("State key cannot be empty")
        self.state[key] = value

    def set_provenance(self, key: str, value: Any) -> None:
        """Set a provenance value on the object."""
        if not key:
            raise ValueError("Provenance key cannot be empty")
        self.provenance[key] = value

    def add_to_attribute_list(self, attr_name: str, item: Any) -> None:
        """Add an item to a list attribute, avoiding duplicates."""
        if not attr_name:
            raise ValueError("Attribute name cannot be empty")
        if item is None or (isinstance(item, str) and not item):
            raise ValueError("Item cannot be empty")
        lst = self.attributes.get(attr_name, [])
        if item not in lst:
            lst.append(item)
            # Sort if all strings
            if lst and all(isinstance(x, str) for x in lst):
                lst.sort()
            self.attributes[attr_name] = lst

    def remove_from_attribute_list(self, attr_name: str, item: Any) -> None:
        """Remove an item from a list attribute."""
        if not attr_name:
            raise ValueError("Attribute name cannot be empty")
        lst = self.attributes.get(attr_name, [])
        if item in lst:
            lst.remove(item)
            if not lst:
                self.attributes.pop(attr_name, None)
            else:
                self.attributes[attr_name] = lst

    def to_dict(self) -> JsonMap:
        """Convert the object to a dictionary representation."""
        return {
            "id": self.id,
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "attributes": dict(sorted(self.attributes.items())),
            "relations": {
                key: sorted(str(value) for value in values)
                for key, values in sorted(self.relations.items())
            },
            "state": dict(sorted(self.state.items())),
            "context": dict(sorted(self.context.items())),
            "provenance": dict(sorted(self.provenance.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModelObject":
        return cls(
            id=str(data["id"]),
            object_type=str(data["object_type"]),
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
