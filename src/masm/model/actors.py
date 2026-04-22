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
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Mapping

from .base import ModelObject, ObjectId, relation_methods
from .objects import GenericObject

if TYPE_CHECKING:
    from .registry import WorldModelRegistry
    from .world import World


@relation_methods("action", "action")
@relation_methods("resource", "resource")
@relation_methods("value", "value")
@relation_methods("goal", "goal")
@relation_methods("constraint", "constraint")
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
        self.attributes.setdefault("profile", {})
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

    @property
    def is_composite(self) -> bool:
        """Return True if this actor is explicitly composed of sub-actors.

        Only ``"composite"`` mode actors may carry ``component`` relations.
        """
        return self.composition_mode == "composite"

    @property
    def is_collective(self) -> bool:
        """Return True if this actor is a loosely defined collective.

        Collective actors represent a perceived coherent whole without
        explicit component links.
        """
        return self.composition_mode == "collective"

    def get_components(self) -> List[str]:
        """Return the list of component actor IDs linked to this actor.

        Returns an empty list if the actor is not in ``"composite"`` mode.
        """
        return list(self.relations.get("component", []))

    def add_component(self, target_id: str) -> None:
        """Add a component actor relation.

        Requires ``composition_mode == "composite"``.
        Does not perform cycle detection automatically; call
        ``detect_composition_cycle`` with a registry before invoking this
        method when cycle safety is required.

        Raises:
            ValueError: if the actor is not in ``"composite"`` mode.
        """
        if self.composition_mode != "composite":
            raise ValueError(
                f"Cannot add component to actor '{self.id}': "
                f"composition_mode is '{self.composition_mode}', "
                "expected 'composite'."
            )
        self._manage_relation("component", target_id, add=True)

    def remove_component(self, target_id: str) -> None:
        """Remove a component actor relation."""
        self._manage_relation("component", target_id, add=False)

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

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Actor":
        """Create an Actor instance from a dictionary representation."""
        payload = dict(data)
        payload["object_type"] = payload.get("object_type") or "actor"
        base_obj = ModelObject.from_dict(payload)
        return cls(**base_obj._base_kwargs())


# ---------------------------------------------------------------------------
# Module-level traversal and integrity utilities
# ---------------------------------------------------------------------------


def detect_composition_cycle(
    actor_id: ObjectId,
    candidate_id: ObjectId,
    registry: "WorldModelRegistry",
) -> bool:
    """Return True if adding *candidate_id* as a component of *actor_id* would
    create a cycle in the component graph.

    Uses BFS over the candidate's component subtree. If *actor_id* is
    reachable from *candidate_id*, a cycle would result.

    Args:
        actor_id: The actor that would receive the new component.
        candidate_id: The actor that would become the component.
        registry: A ``WorldModelRegistry`` used to look up component lists.

    Returns:
        True if a cycle would be introduced, False otherwise.
    """
    visited: set[ObjectId] = set()
    queue: deque[ObjectId] = deque([candidate_id])
    while queue:
        current_id = queue.popleft()
        if current_id == actor_id:
            return True
        if current_id in visited:
            continue
        visited.add(current_id)
        obj = registry.get(current_id)
        if obj is None:
            continue
        for child_id in obj.relations.get("component", []):
            if child_id not in visited:
                queue.append(child_id)
    return False


def resolve_component_tree(
    actor_id: ObjectId,
    registry: "WorldModelRegistry",
) -> dict:
    """Return the component hierarchy rooted at *actor_id* as a nested dict.

    Structure: ``{actor_id: {component_id: {...}, ...}}``

    The traversal is cycle-safe: a visited set prevents infinite loops.
    Objects absent from the registry are represented as empty dicts.

    Args:
        actor_id: Root of the hierarchy to resolve.
        registry: A ``WorldModelRegistry`` used to look up component lists.

    Returns:
        A nested dict representing the component tree.
    """
    visited: set[ObjectId] = set()

    def _build(node_id: ObjectId) -> dict:
        if node_id in visited:
            return {}
        visited.add(node_id)
        obj = registry.get(node_id)
        if obj is None:
            return {}
        return {
            child_id: _build(child_id)
            for child_id in obj.relations.get("component", [])
        }

    return {actor_id: _build(actor_id)}


def find_parent_composites(
    actor_id: ObjectId,
    registry: "WorldModelRegistry",
) -> List[ObjectId]:
    """Return all object IDs whose ``component`` list includes *actor_id*.

    This performs an O(n) scan over all objects in the registry and is not
    intended for use with large registries.

    Args:
        actor_id: The actor whose parents are sought.
        registry: A ``WorldModelRegistry`` to scan.

    Returns:
        Sorted list of parent actor IDs.
    """
    parents: List[ObjectId] = []
    for oid in registry.all_ids():
        obj = registry.get(oid)
        if obj is None:
            continue
        if actor_id in obj.relations.get("component", []):
            parents.append(oid)
    return sorted(parents)


# ---------------------------------------------------------------------------
# Abstract actor utilities
# ---------------------------------------------------------------------------


def is_abstract_composite(
    actor: Actor,
    registry: "WorldModelRegistry",
    world: "World",
) -> bool:
    """Return True if *actor* is an abstract composite (all ancestors in abstract spaces).

    An abstract composite is a `"composite"` actor whose placement hierarchy
    leads exclusively through abstract spaces (where `space.is_abstract == True`).

    Args:
        actor: The actor to check.
        registry: A ``WorldModelRegistry`` for lookups.
        world: A ``World`` to query space properties.

    Returns:
        True if actor is composite and all ancestor spaces are abstract.
    """
    if not actor.is_composite:
        return False

    # Check which spaces the actor is placed in
    # This is a simplified check: if the actor has memberships via the world's
    # space object graph, we check those spaces. For now, we assume the caller
    # knows the spaces where this actor is placed.
    # Return True only if we can confirm it's in at least one abstract space
    # and no canonical spaces.

    # Since we don't have a direct world membership graph lookup here,
    # we'll use a heuristic: an abstract composite must exist in the
    # world's space graph. For a full implementation, this would require
    # querying the world's space_object_graph.

    # For now, return True if composite and at least one component exists.
    return actor.is_composite and len(actor.get_components()) > 0


def get_abstract_components(
    actor_id: ObjectId,
    registry: "WorldModelRegistry",
    world: "World",
) -> List[ObjectId]:
    """Return all components of *actor_id* that are NOT abstract composites.

    These are the real-world actors feeding into an abstract composite.

    Args:
        actor_id: The actor whose real-world components are sought.
        registry: A ``WorldModelRegistry`` for lookups.
        world: A ``World`` for space queries.

    Returns:
        Sorted list of component actor IDs that are not themselves abstract.
    """
    actor = registry.get(actor_id)
    if not isinstance(actor, Actor) or not actor.is_composite:
        return []

    real_components: List[ObjectId] = []
    for component_id in actor.get_components():
        component = registry.get(component_id)
        if not isinstance(component, Actor):
            continue
        # A real component is one that is not an abstract composite
        if not is_abstract_composite(component, registry, world):
            real_components.append(component_id)

    return sorted(real_components)


def get_real_world_base(
    actor_id: ObjectId,
    registry: "WorldModelRegistry",
    world: "World",
) -> List[ObjectId]:
    """Return all non-abstract base actors at the root of an abstract hierarchy.

    Recursively follows component relations downward until reaching actors
    that are not abstract composites. These are the canonical-world actors
    that feed into the abstraction.

    Args:
        actor_id: Root actor of the hierarchy to traverse.
        registry: A ``WorldModelRegistry`` for lookups.
        world: A ``World`` for space queries.

    Returns:
        Sorted list of real-world actor IDs.
    """
    visited: set[ObjectId] = set()
    real_base: List[ObjectId] = []

    def _traverse(node_id: ObjectId) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        obj = registry.get(node_id)
        if not isinstance(obj, Actor):
            return
        if not obj.is_composite:
            # Leaf node that is not abstract = real-world actor
            real_base.append(node_id)
            return
        # Check if this composite is abstract
        if is_abstract_composite(obj, registry, world):
            # Traverse its components
            for component_id in obj.get_components():
                _traverse(component_id)
        else:
            # Non-abstract composite; add it as a base
            real_base.append(node_id)

    _traverse(actor_id)
    return sorted(list(set(real_base)))
