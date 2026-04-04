from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple, Type, Union

SchemaVersion = str
ObjectId = str
RelationMap = Dict[str, List[ObjectId]]
JsonMap = Dict[str, Any]

@dataclass
class ModelObject:
    """A base class for all objects in the model. 
    It contains the common fields and methods that all objects share.
    It is volonteerily designed to be as simple as possible, and to be easily extendable by subclasses.
    It should not contain any logic that is specific to a particular type of object, but rather should be a generic container for data that can be used by subclasses.
    No specific hypothesis about the actors, resources, perceptions, objectifs should be included 
    """
    id: ObjectId
    type: str
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


    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "type": self.type,
            "attributes": self.attributes,
            "relations": self.relations,
        }