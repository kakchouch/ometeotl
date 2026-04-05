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
from typing import Any, Dict, List, Mapping, Optional

from .objects import GenericObject

# local aliases
JsonDict = Mapping[str, Any]
ObjectId = str

def _default_schema_version() -> str:
    return "1.0"

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
        if self.object_type != "actor":
           self.object_type = "actor"

        self.attributes.setdefault("kind", "generic")
        self.attributes.setdefault("tags",[])
        self.attributes.setdefault("roles",[])
        self.attributes.setdefault("profiles",{})
        self.attributes.setdefault("emergent", False)
        self.attributes.setdefault("composition_mode", "standalone")

        @property
        def kind(self) -> str:
            """Returns the actor's, kind.
            Typical examples include :
            -"individual": a single person or entity;
            -"group": a collection of individuals or entities;
            -organization: a structured group with specific roles and functions;
            -emergent: a loosely defined entity emerging from the perceptions of other actors."""
            
            value = self.attributes.get("kind","generic")
            return str(value) if value is not None else "generic"

        @kind.setter
        def kind(self, value: str) -> None:
            """Sets the actor's kind."""
            if not value:
                raise ValueError("Kind cannot be empty")
            self.attributes["kind"] = value

        @property
        def tags(self) -> List[str]:
            """Returns the actor's tags, which are simple labels that can be used for categorization, filtering, or search."""
            value = self.attributes.get("tags",[])
            return sorted(list(value)) if value is not None else []

        def add_tag(self, tag: str) -> None:
            """Adds a tag to the actor."""
            if not tag:
                raise ValueError("Tag cannot be empty")
            tags = set(self.attributes.get("tags",[]))
            tags.add(tag)
            self.attributes["tags"] = sorted(list(tags))

        @property
        def roles(self) -> List[str]:
            """Returns the actor's roles, which are specific functions or positions that the actor can assume within a particular context or interaction."""
            roles = self.attributes.get("roles",[])
            return sorted(list(roles)) if roles is not None else []

        def add_role(self, role: str) -> None:
            """Adds a role to the actor."""
            if not role:
                raise ValueError("Role cannot be empty")
            roles = set(self.attributes.get("roles",[]))
            if role not in roles:
                roles.append(role)
            self.attributes["roles"] = sorted(list(roles))
        
        @property
        def profile(self) -> JsonMap:
            """ Returns the free-form profile of the actor, which are structured data that can be used to capture specific characteristics, preferences, or attributes of the actor in a more detailed and organized way.
            This dictionnary is intentionally open-endend and can contain
            modeling details such as category-specific metadata,
            identifiers, demographic infor"""
            value = self.attributes.get("profile",{})
            return dict(value) if isinstance(value, Mapping) else {}

        def set_profile_item(self, key:str, value: Any) -> None:
            """Sets a specific item in the actor's profile."""
            if not key:
                raise ValueError("Profile key cannot be empty")
            profile = self.profile
            profile[key] = value
            self.attributes["profile"] = dict(sorted(profile.items()))

        @property
        def emergent(self) -> bool:
            """Returns whether the actor is emergent, meaning it is a loosely defined entity emerging from the perceptions of other actors."""
            value = self.attributes.get("emergent", False)
            return bool(value)
        
        @emergent.setter
        def emergent(self, value: bool) -> None:
            """Sets whether the actor is emergent."""
            self.attributes["emergent"] = bool(value)
        
        @property
        def composition_mode(self) -> str:
            """Returns the actor's composition mode, which indicates how the actor is composed of other actors if it is a composite entity. 
            Typical values include:
            - "standalone": the actor is not composed of other actors;
            - "composite": the actor is composed of other actors, which are explicitly linked to it through relations;
            - "collective": the actor is a loosely defined collection of other actors, which are not explicitly linked to it but are perceived as a coherent whole.
            - "perceived": the actor is an emergent entity perceived by other actors as a coherent whole, without a clear internal structure or composition.
            - "projected": the actor is a projected entity that may not have a clear existence but is treated as an actor for modeling purposes or through other actors interactions."""
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
    # Important idea : 
    # In this architecture, actions, resources, goals etc. are not stored as 
    # complex objects directly in the actor, but rather as relations to other model objects.
    # This allows for greater flexibility and extensibility, as well as a clearer separation of concerns.
    # It ensures fidelity with  ModelObject.relations, which is the canonical place for storing links between model objects.

    def add_action(self, action_id: ObjectId) -> None:
        """Adds an action to the actor by creating a relation to the action object."""
        if not action_id:
            raise ValueError("Action ID cannot be empty")
        actions = set(self.relations.get("actions",[]))
        actions.add(action_id)
        self.relations["actions"] = sorted(list(actions))

    def remove_action(self, action_id: ObjectId) -> None:
        """Removes an action from the actor by removing the relation to the action object."""
        if not action_id:
            raise ValueError("Action ID cannot be empty")
        actions = set(self.relations.get("actions",[]))
        if action_id in actions:
            actions.remove(action_id)
            self.relations["actions"] = sorted(list(actions))

    def add_resource(self, resource_id: ObjectId) -> None:
        """Adds a resource to the actor by creating a relation to the resource object."""
        if not resource_id:
            raise ValueError("Resource ID cannot be empty")
        resources = set(self.relations.get("resources",[]))
        resources.add(resource_id)
        self.relations["resources"] = sorted(list(resources))

    def remove_resource(self, resource_id: ObjectId) -> None:
        """Removes a resource from the actor by removing the relation to the resource object."""
        if not resource_id:
            raise ValueError("Resource ID cannot be empty")
        resources = set(self.relations.get("resources",[]))
        if resource_id in resources:
            resources.remove(resource_id)
            self.relations["resources"] = sorted(list(resources))

    def add_value(self, value_id: ObjectId) -> None:
        """Adds a value to the actor by creating a relation to the value object."""
        if not value_id:
            raise ValueError("Value ID cannot be empty")
        values = set(self.relations.get("values",[]))
        values.add(value_id)
        self.relations["values"] = sorted(list(values))

    def remove_value(self, value_id: ObjectId) -> None:
        """Removes a value from the actor by removing the relation to the value object."""
        if not value_id:
            raise ValueError("Value ID cannot be empty")
        values = set(self.relations.get("values",[]))
        if value_id in values:
            values.remove(value_id)
            self.relations["values"] = sorted(list(values))

    def add_goal(self, goal_id: ObjectId) -> None:
        """Adds a goal to the actor by creating a relation to the goal object."""
        if not goal_id:
            raise ValueError("Goal ID cannot be empty")
        goals = set(self.relations.get("pursues_goal",[]))
        goals.add(goal_id)
        self.relations["pursues_goal"] = sorted(list(goals))

    def remove_goal(self, goal_id: ObjectId) -> None:
        """Removes a goal from the actor by removing the relation to the goal object."""
        if not goal_id:
            raise ValueError("Goal ID cannot be empty")
        goals = set(self.relations.get("pursues_goal",[]))
        if goal_id in goals:
            goals.remove(goal_id)
            self.relations["pursues_goal"] = sorted(list(goals))

    def add_constraint(self, constraint_id: ObjectId) -> None:
        """Adds a constraint to the actor by creating a relation to the constraint object."""
        if not constraint_id:
            raise ValueError("Constraint ID cannot be empty")
        constraints = set(self.relations.get("subject_to",[]))
        constraints.add(constraint_id)
        self.relations["subject_to"] = sorted(list(constraints))

    def remove_constraint(self, constraint_id: ObjectId) -> None:
        """Removes a constraint from the actor by removing the relation to the constraint object."""
        if not constraint_id:
            raise ValueError("Constraint ID cannot be empty")
        constraints = set(self.relations.get("subject_to",[]))
        if constraint_id in constraints:
            constraints.remove(constraint_id)
            self.relations["subject_to"] = sorted(list(constraints))

    def add_component(self, actor_id: ObjectId) -> None:
        """Adds a component actor to the actor by creating a relation to the component actor object."""
        if not actor_id:
            raise ValueError("Actor ID cannot be empty")
        components = set(self.relations.get("composed_of",[]))
        components.add(actor_id)
        self.relations["composed_of"] = sorted(list(components))

    def remove_component(self, actor_id: ObjectId) -> None:
        """Removes a component actor from the actor by removing the relation to the component actor object."""
        if not actor_id:
            raise ValueError("Actor ID cannot be empty")
        components = set(self.relations.get("composed_of",[]))
        if actor_id in components:
            components.remove(actor_id)
            self.relations["composed_of"] = sorted(list(components))
    
    def add_membership(self, actor_id: ObjectId) -> None:
        """Adds a membership relation to another actor by creating a relation to the other actor object."""
        if not actor_id:
            raise ValueError("Actor ID cannot be empty")
        memberships = set(self.relations.get("member_of",[]))
        memberships.add(actor_id)
        self.relations["member_of"] = sorted(list(memberships))

    def remove_membership(self, actor_id: ObjectId) -> None:
        """Removes a membership relation to another actor by removing the relation to the other actor object."""
        if not actor_id:
            raise ValueError("Actor ID cannot be empty")
        memberships = set(self.relations.get("member_of",[]))
        if actor_id in memberships:
            memberships.remove(actor_id)
            self.relations["member_of"] = sorted(list(memberships))


    def add_dependency(self, actor_id: ObjectId) -> None:
        """Adds a dependency relation to another actor by creating a relation to the other actor object."""
        if not actor_id:
            raise ValueError("Actor ID cannot be empty")
        dependencies = set(self.relations.get("depends_on",[]))
        dependencies.add(actor_id)
        self.relations["depends_on"] = sorted(list(dependencies))

    def remove_dependency(self, actor_id: ObjectId) -> None:
        """Removes a dependency relation to another actor by removing the relation to the other actor object."""
        if not actor_id:
            raise ValueError("Actor ID cannot be empty")
        dependencies = set(self.relations.get("depends_on",[]))
        if actor_id in dependencies:
            dependencies.remove(actor_id)
            self.relations["depends_on"] = sorted(list(dependencies))   

     def add_cooperation(self, actor_id: ObjectId) -> None:
        """Declare a cooperative relation with another actor."""
        self.add_relation("cooperates_with", actor_id)

    def remove_cooperation(self, actor_id: ObjectId) -> None:
        """Remove a cooperation relation."""
        self.remove_relation("cooperates_with", actor_id)

    def add_conflict(self, actor_id: ObjectId) -> None:
        """Declare a conflict relation with another actor."""
        self.add_relation("conflicts_with", actor_id)

    def remove_conflict(self, actor_id: ObjectId) -> None:
        """Remove a conflict relation.""" 
        self.remove_relation("conflicts_with", actor_id)

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Actor instance to a dictionary representation."""
        return {
            "id": self.id,
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "attributes": dict(self.attributes),
            "relations": {
                key: sorted(list(set(value))) for key, value in dict(self.relations).items()
            },
            "state": dict(self.state),
            "context": dict(self.context),
            "provenance": dict(self.provenance),
        }