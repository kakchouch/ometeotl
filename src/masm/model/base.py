from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple, object_type, Union

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
    It is volonteerily designed to be as simple as possible, and to be easily extendable by subclasses.
    It should not contain any logic that is specific to a particular object_type of object, but rather should be a generic container for data that can be used by subclasses.
    No specific hypothesis about the actors, resources, perceptions, objectifs should be included 
    """
    id: ObjectId
    object_type: str
    schema_version: SchemaVersion = field(default_factory=_default_schema_version)
    attributes: JsonMap = field(default_factory=dict)
    relations: RelationMap = field(default_factory=dict)
    state: JsonMap = field(default_factory=dict)
    context: JsonMap = field(default_factory=dict)
    provenance: JsonMap = field(default_factory=dict)

    def add_relation(self, name: str, target_id: ObjectId)-> None:
        if not name:
            raise ValueError("Relation name cannot be empty")
        if not target_id:
            raise ValueError("Target ID cannot be empty")
        self.relations.setdefault(name, [])
        if target_id not in self.relations[name]:
            self.relations[name].append(target_id)


    def remove_relation(self, name: str, target_id: ObjectId) -> None:
        if name not in self.relations:
            return
        self.relations[name] = [
            existing_id for existing_id in self.relations[name] 
            if existing_id != target_id
            ]
        if not self.relations[name]:
            del self.relations[name]

    def set_attribute(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("Attribute key cannot be empty")
        self.attributes[key] = value

    def set_state(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("State key cannot be empty")
        self.state[key] = value

    def set_provenance(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("Provenance key cannot be empty")
        self.provenance[key] = value

    


    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "attributes": dict(sorted(self.attributes.items())),
            "relations": {
                key: sorted(str(value) for value in values)
                for key, values in sorted(self.relations.items())
            }
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