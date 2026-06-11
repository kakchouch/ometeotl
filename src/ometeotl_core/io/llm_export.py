"""LLM-oriented export for model objects.

This module provides utilities to convert model objects into views optimized
for consumption by language models, clearly distinguishing:
- reality (ontological state)
- perception (actor-specific views)
- epistemic status (certain, believed, hypothesis, projected, error)

Requirement F-5: A dedicated language-model view must explicitly distinguish
reality, perception, belief, hypothesis, and projection.

Axioms A-9, A-10: Each actor has partial, biased perception; decisions depend
on perception, not ontological reality.
"""

from __future__ import annotations

from typing import Any, Mapping, Set, Optional
from dataclasses import dataclass, field

from ometeotl_core.model.perception import (
    _sort_key_perceived_membership,
    _sort_key_perceived_relation,
    _sort_key_perceived_component_link,
)


@dataclass
class LLMViewContext:
    """Context for building LLM views, tracking circular references and options.

    Attributes:
        include_provenance: Include provenance metadata in output.
        include_context: Include context metadata in output.
        include_state: Include dynamic state in output.
        include_relations: Include relations to other objects (as IDs).
        include_attributes: Include descriptive attributes in output.
        seen_ids: Set of already-visited object IDs (for cycle detection).
        reference_style: How to handle cross-references: "id" (object IDs),
            "path" (hierarchical path), or "full" (inline object if not circular).
    """

    include_provenance: bool = False
    include_context: bool = False
    include_state: bool = True
    include_relations: bool = True
    include_attributes: bool = True
    seen_ids: Set[str] = field(default_factory=set)
    reference_style: str = "id"  # "id", "path", or "full"

    def copy(self) -> LLMViewContext:
        """Create a shallow copy of this context (seen_ids is shared)."""
        return LLMViewContext(
            include_provenance=self.include_provenance,
            include_context=self.include_context,
            include_state=self.include_state,
            include_relations=self.include_relations,
            include_attributes=self.include_attributes,
            seen_ids=self.seen_ids,
            reference_style=self.reference_style,
        )

    def mark_visited(self, obj_id: str) -> None:
        """Record that we've visited an object (for cycle detection)."""
        self.seen_ids.add(obj_id)

    def is_visited(self, obj_id: str) -> bool:
        """Check if an object has been visited."""
        return obj_id in self.seen_ids


class LLMViewBuilder:
    """Builder for language-model-oriented views of model objects.

    Converts model objects to structured dictionaries optimized for LLM
    consumption, emphasizing:
    - Epistemic clarity (certain vs. believed vs. hypothesis vs. projected vs. error)
    - Reality/perception separation
    - Deterministic structure
    - Explicit handling of circular references

    Usage:
        builder = LLMViewBuilder()
        view = builder.world_view(world, context=LLMViewContext())
    """

    def __init__(self) -> None:
        """Initialize the builder."""
        # Stateless builder; all export settings live in LLMViewContext.
        return

    def _build_base_view(
        self,
        obj_id: str,
        obj_type: str,
        data: Mapping[str, Any],
        context: LLMViewContext,
    ) -> dict[str, Any]:
        """Build the base view structure for any model object.

        Args:
            obj_id: The object's unique identifier.
            obj_type: The canonical type of the object (e.g., "actor", "world").
            data: The object's data (attributes, relations, state, etc.).
            context: LLMViewContext controlling what to include.

        Returns:
            A dictionary with id, type, and optionally attributes, state, relations.
        """
        view: dict[str, Any] = {
            "id": obj_id,
            "type": obj_type,
        }

        if context.include_attributes:
            attributes = data.get("attributes", {})
            if attributes:
                view["attributes"] = dict(attributes)

        if context.include_state:
            state = data.get("state", {})
            if state:
                view["state"] = dict(state)

        if context.include_relations:
            relations = data.get("relations", {})
            if relations:
                # Format relations as ID references
                view["relations"] = {
                    key: sorted(str(rel_id) for rel_id in rel_ids)
                    for key, rel_ids in relations.items()
                    if rel_ids
                }

        if context.include_provenance:
            provenance = data.get("provenance", {})
            if provenance:
                view["provenance"] = dict(provenance)

        if context.include_context:
            ctx = data.get("context", {})
            if ctx:
                view["context"] = dict(ctx)

        return view

    def _build_reality_block(
        self,
        data: Mapping[str, Any],
        context: LLMViewContext,
    ) -> dict[str, Any]:
        """Build the ontological slice of a model object."""
        reality: dict[str, Any] = {}

        if context.include_attributes:
            attributes = data.get("attributes", {})
            if attributes:
                reality["attributes"] = dict(attributes)

        if context.include_state:
            state = data.get("state", {})
            if state:
                reality["state"] = dict(state)

        if context.include_relations:
            relations = data.get("relations", {})
            if relations:
                reality["relations"] = {
                    key: sorted(str(rel_id) for rel_id in rel_ids)
                    for key, rel_ids in relations.items()
                    if rel_ids
                }

        if context.include_provenance:
            provenance = data.get("provenance", {})
            if provenance:
                reality["provenance"] = dict(provenance)

        if context.include_context:
            ctx = data.get("context", {})
            if ctx:
                reality["context"] = dict(ctx)

        return reality

    def _build_epistemic_block(
        self,
        status: str,
        meaning: str,
        has_perception: bool = False,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "meaning": meaning,
            "distinctions": [
                "reality",
                "perception",
                "belief",
                "hypothesis",
                "projection",
            ],
            "has_perception": has_perception,
        }

    def _attach_standard_blocks(
        self,
        view: dict[str, Any],
        *,
        reality: Mapping[str, Any],
        epistemic_status: str,
        epistemic_meaning: str,
        has_perception: bool = False,
        perception: Any = None,
    ) -> dict[str, Any]:
        """Attach the standard LLM blocks to a view and return it."""
        view["reality"] = dict(reality)
        view["perception"] = perception
        view["epistemic"] = self._build_epistemic_block(
            status=epistemic_status,
            meaning=epistemic_meaning,
            has_perception=has_perception,
        )
        return view

    def _build_perception_payload(self, perception: Any) -> dict[str, Any]:
        """Build the raw perceived structures for LLM consumption."""
        return {
            "perceived_spaces": {
                space_id: space_view.to_dict()
                for space_id, space_view in sorted(
                    getattr(perception, "perceived_spaces", {}).items()
                )
            },
            "perceived_memberships": [
                membership.to_dict()
                for membership in sorted(
                    getattr(perception, "perceived_memberships", []),
                    key=_sort_key_perceived_membership,
                )
            ],
            "perceived_relations": [
                relation.to_dict()
                for relation in sorted(
                    getattr(perception, "perceived_relations", []),
                    key=_sort_key_perceived_relation,
                )
            ],
            "perceived_component_links": [
                link.to_dict()
                for link in sorted(
                    getattr(perception, "perceived_component_links", []),
                    key=_sort_key_perceived_component_link,
                )
            ],
        }

    def _build_epistemic_status_groups(
        self, perception: Any
    ) -> dict[str, list[dict[str, Any]]]:
        """Group perceived items by epistemic status for stable LLM output."""
        grouped: dict[str, list[dict[str, Any]]] = {}

        for space_id, space_view in sorted(
            getattr(perception, "perceived_spaces", {}).items()
        ):
            grouped.setdefault(space_view.epistemic_status, []).append(
                {"kind": "space", "id": space_id}
            )

        for membership in sorted(
            getattr(perception, "perceived_memberships", []),
            key=_sort_key_perceived_membership,
        ):
            grouped.setdefault(membership.epistemic_status, []).append(
                {
                    "kind": "membership",
                    "object_id": membership.membership.object_id,
                    "space_id": membership.membership.space_id,
                }
            )

        for relation in sorted(
            getattr(perception, "perceived_relations", []),
            key=_sort_key_perceived_relation,
        ):
            grouped.setdefault(relation.epistemic_status, []).append(
                {
                    "kind": "relation",
                    "source_space_id": relation.relation.source_space_id,
                    "target_space_id": relation.relation.target_space_id,
                }
            )

        for link in sorted(
            getattr(perception, "perceived_component_links", []),
            key=_sort_key_perceived_component_link,
        ):
            grouped.setdefault(link.epistemic_status, []).append(
                {
                    "kind": "component_link",
                    "composite_id": link.composite_id,
                    "component_id": link.component_id,
                }
            )

        return {status: grouped[status] for status in sorted(grouped)}

    def world_view(
        self,
        world: Any,
        context: Optional[LLMViewContext] = None,
    ) -> dict[str, Any]:
        """Build an LLM view of a World object.

        The view includes:
        - World metadata (id, type, attributes)
        - Member objects (actors, spaces, resources) as ID references
        - World state and relations
        - Space hierarchy

        Args:
            world: The World object (expects to_dict() and model_registry).
            context: LLMViewContext controlling output. Defaults to sensible LLM-friendly defaults.

        Returns:
            A dictionary suitable for LLM consumption.
        """
        if context is None:
            context = LLMViewContext()

        context.mark_visited(world.id)

        world_dict = world.to_dict()
        view = self._build_base_view(
            world.id,
            "world",
            world_dict,
            context,
        )
        self._attach_standard_blocks(
            view,
            reality=self._build_reality_block(world_dict, context),
            epistemic_status="certain",
            epistemic_meaning="Ontological world state",
        )

        # Add member objects summary
        members_summary = {
            "total_actors": 0,
            "total_spaces": 0,
            "total_resources": 0,
        }

        if hasattr(world, "model_registry") and world.model_registry:
            registry = world.model_registry
            registered_objects = [registry.get(obj_id) for obj_id in registry.all_ids()]
            registered_objects = [obj for obj in registered_objects if obj is not None]

            members_summary["total_actors"] = sum(
                1 for obj in registered_objects if obj.object_type == "actor"
            )
            members_summary["total_spaces"] = sum(
                1 for obj in registered_objects if obj.object_type == "space"
            )
            members_summary["total_resources"] = sum(
                1 for obj in registered_objects if obj.object_type == "resource"
            )

            actors = sorted(
                obj.id for obj in registered_objects if obj.object_type == "actor"
            )
            spaces = sorted(
                obj.id for obj in registered_objects if obj.object_type == "space"
            )
            resources = sorted(
                obj.id for obj in registered_objects if obj.object_type == "resource"
            )

            # Include member IDs
            view["members"] = {
                "actors": actors,
                "spaces": spaces,
                "resources": resources,
            }

        view["members_summary"] = members_summary

        return view

    def actor_view(
        self,
        actor: Any,
        context: Optional[LLMViewContext] = None,
        include_perception: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Build an LLM view of an Actor object.

        The view includes:
        - Actor metadata (id, type, kind, attributes)
        - Actor's capabilities (actions, resources)
        - Actor's objectives (goals, values, constraints)
        - Optional: Actor's perception (if provided)

        Args:
            actor: The Actor object.
            context: LLMViewContext controlling output.
            include_perception: Optional Perception object for this actor.

        Returns:
            A dictionary suitable for LLM consumption.
        """
        if context is None:
            context = LLMViewContext()

        context.mark_visited(actor.id)

        actor_dict = actor.to_dict()
        view = self._build_base_view(
            actor.id,
            "actor",
            actor_dict,
            context,
        )
        perception_view = (
            self.perception_view(include_perception, context)
            if include_perception is not None
            else None
        )
        self._attach_standard_blocks(
            view,
            reality=self._build_reality_block(actor_dict, context),
            epistemic_status="mixed" if include_perception is not None else "certain",
            epistemic_meaning=(
                "Actor reality plus an attached perception view"
                if include_perception is not None
                else "Ontological actor state"
            ),
            has_perception=include_perception is not None,
            perception=perception_view,
        )

        # Expose key actor properties
        kind = actor.attributes.get("kind", "generic")
        view["kind"] = str(kind)

        # Highlight key relations for actors
        if context.include_relations:
            relations = actor_dict.get("relations", {})
            view["capabilities"] = {
                "actions": relations.get("action", []),
                "resources": relations.get("resource", []),
            }
            view["objectives"] = {
                "goals": relations.get("goal", []),
                "values": relations.get("value", []),
            }
            view["constraints"] = relations.get("constraint", [])

        return view

    def strategy_view(
        self,
        strategy: Any,
        context: Optional[LLMViewContext] = None,
    ) -> dict[str, Any]:
        """Build an LLM view of a Strategy object.

        The view includes:
        - Strategy metadata (id, type)
        - Action being modeled
        - Projected outcomes and branch information
        - Uncertainty/risk assessment

        Args:
            strategy: The Strategy object.
            context: LLMViewContext controlling output.

        Returns:
            A dictionary suitable for LLM consumption.
        """
        if context is None:
            context = LLMViewContext()

        context.mark_visited(strategy.id)

        strategy_dict = strategy.to_dict()
        view = self._build_base_view(
            strategy.id,
            "strategy",
            strategy_dict,
            context,
        )
        self._attach_standard_blocks(
            view,
            reality=self._build_reality_block(strategy_dict, context),
            epistemic_status="certain",
            epistemic_meaning="Ontological strategy structure",
        )

        # Highlight strategy structure
        if context.include_relations:
            relations = strategy_dict.get("relations", {})
            view["structure"] = {
                "action": relations.get("action", []),
                "outcome_branches": relations.get("outcome_branch", []),
                "assumptions": relations.get("projection_assumption", []),
            }

        # Expose the strategy tree with branch-level projected states
        raw_nodes = strategy_dict.get("nodes") or []
        if raw_nodes:
            view["tree"] = {
                "root_node_id": strategy_dict.get("root_node_id"),
                "nodes": [
                    {
                        "node_id": node["node_id"],
                        "action_id": node["action_id"],
                        "source_perception_id": node.get("source_perception_id"),
                        "branches": [
                            {
                                "branch_id": branch["branch_id"],
                                "label": branch.get("label"),
                                "child_node_id": branch.get("child_node_id"),
                                "probability": branch.get("probability"),
                                "projected_perception_id": (
                                    branch["projected_state"]["perception"]["id"]
                                    if branch.get("projected_state")
                                    else None
                                ),
                            }
                            for branch in (node.get("outcome_branches") or [])
                        ],
                    }
                    for node in raw_nodes
                ],
            }

        return view

    def goal_view(
        self,
        goal: Any,
        context: Optional[LLMViewContext] = None,
    ) -> dict[str, Any]:
        """Build an LLM view of a Goal object.

        The view includes:
        - Goal metadata (id, type)
        - Goal description and scope
        - Goal's relation to actor and target space

        Args:
            goal: The Goal object.
            context: LLMViewContext controlling output.

        Returns:
            A dictionary suitable for LLM consumption.
        """
        if context is None:
            context = LLMViewContext()

        context.mark_visited(goal.id)

        goal_dict = goal.to_dict()
        view = self._build_base_view(
            goal.id,
            "goal",
            goal_dict,
            context,
        )
        self._attach_standard_blocks(
            view,
            reality=self._build_reality_block(goal_dict, context),
            epistemic_status="certain",
            epistemic_meaning="Ontological goal structure",
        )

        if context.include_relations:
            relations = goal_dict.get("relations", {})
            view["structure"] = {
                "actor": relations.get("actor", []),
                "target_space": relations.get("target_space", []),
                "related_goals": relations.get("parent_goal", []),
            }

        return view

    def perception_view(
        self,
        perception: Any,
        context: Optional[LLMViewContext] = None,
    ) -> dict[str, Any]:
        """Build an LLM view of a Perception object.

        The view includes:
        - Epistemic status markers (certain, believed, hypothesis, projected, error)
        - Perceived spaces, memberships, relations
        - Perceived component links (for composite actors)
        - Noise/distortion metadata

        Args:
            perception: The Perception object.
            context: LLMViewContext controlling output.

        Returns:
            A dictionary suitable for LLM consumption.
        """
        if context is None:
            context = LLMViewContext()

        context.mark_visited(perception.id)

        perception_dict = perception.to_dict()
        view = self._build_base_view(
            perception.id,
            "perception",
            perception_dict,
            context,
        )
        perception_payload = self._build_perception_payload(perception)

        self._attach_standard_blocks(
            view,
            reality={
                "id": perception.id,
                "actor_id": perception_dict.get("actor_id"),
                "source_id": perception_dict.get("source_id"),
                "timestamp": perception_dict.get("timestamp"),
            },
            epistemic_status="mixed",
            epistemic_meaning="Perception groups reality into epistemic confidence levels",
            has_perception=True,
            perception=perception_payload,
        )

        view["epistemic_statuses"] = self._build_epistemic_status_groups(perception)
        view["epistemic_meanings"] = {
            "certain": "Directly observed, no uncertainty",
            "believed": "Inferred or remembered, probably true",
            "hypothesis": "Speculative, may or may not hold",
            "projected": "Anticipated based on a model but not observed",
            "error": "Identified as incorrect (diagnosed hallucination)",
        }
        return view

    def space_view(
        self,
        space: Any,
        context: Optional[LLMViewContext] = None,
    ) -> dict[str, Any]:
        """Build an LLM view of a Space object.

        The view includes:
        - Space metadata (id, type, kind)
        - Space membership (member objects)
        - Space relations (connections to other spaces)
        - Dimensionality and metrics

        Args:
            space: The Space object.
            context: LLMViewContext controlling output.

        Returns:
            A dictionary suitable for LLM consumption.
        """
        if context is None:
            context = LLMViewContext()

        context.mark_visited(space.id)

        space_dict = space.to_dict()
        view = self._build_base_view(
            space.id,
            "space",
            space_dict,
            context,
        )
        self._attach_standard_blocks(
            view,
            reality=self._build_reality_block(space_dict, context),
            epistemic_status="certain",
            epistemic_meaning="Ontological space state",
        )

        # Highlight space properties
        view["properties"] = {
            "is_abstract": space_dict.get("is_abstract", False),
            "is_temporal": space_dict.get("is_temporal", False),
        }

        if context.include_relations:
            relations = space_dict.get("relations", {})
            view["structure"] = {
                "members": relations.get("member", []),
                "parent_spaces": relations.get("parent_space", []),
                "child_spaces": relations.get("child_space", []),
            }

        return view


# Convenience functions for common use cases


def actor_to_llm_view(
    actor: Any,
    perception: Optional[Any] = None,
    include_provenance: bool = False,
) -> dict[str, Any]:
    """Export an actor to an LLM view, optionally with perception.

    Args:
        actor: The Actor object to export.
        perception: Optional Perception of this actor.
        include_provenance: Whether to include provenance metadata.

    Returns:
        An LLM-friendly dictionary representation.
    """
    builder = LLMViewBuilder()
    context = LLMViewContext(include_provenance=include_provenance)
    return builder.actor_view(actor, context=context, include_perception=perception)


def world_to_llm_view(
    world: Any,
    include_provenance: bool = False,
) -> dict[str, Any]:
    """Export a world to an LLM view.

    Args:
        world: The World object to export.
        include_provenance: Whether to include provenance metadata.

    Returns:
        An LLM-friendly dictionary representation.
    """
    builder = LLMViewBuilder()
    context = LLMViewContext(include_provenance=include_provenance)
    return builder.world_view(world, context=context)


def perception_to_llm_view(
    perception: Any,
    include_provenance: bool = False,
) -> dict[str, Any]:
    """Export a perception to an LLM view.

    Args:
        perception: The Perception object to export.
        include_provenance: Whether to include provenance metadata.

    Returns:
        An LLM-friendly dictionary representation.
    """
    builder = LLMViewBuilder()
    context = LLMViewContext(include_provenance=include_provenance)
    return builder.perception_view(perception, context=context)
