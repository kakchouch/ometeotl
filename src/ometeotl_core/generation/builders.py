"""Object builders for contextual generation."""

from __future__ import annotations

from typing import Any, Mapping

from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import (
    Perception,
    PerceivedComponentLink,
    PerceivedMembership,
    PerceivedRelation,
    PerceivedSpace,
)
from ometeotl_core.model.resources import Resource
from ometeotl_core.model.space_relations import SpaceRelation
from ometeotl_core.model.spaces import Space, SpaceObjectMembership
from ometeotl_core.model.strategies import Strategy, StrategyNode
from ometeotl_core.model.world import World

from .context import GenerationContext


def _base_kwargs(context: GenerationContext) -> dict[str, Any]:
    return {
        "id": context.id,
        "attributes": context.merged_attributes(),
        "relations": context.normalized_relations(),
        "state": dict(context.state),
        "context": context.merged_context(),
        "provenance": dict(context.provenance),
    }


def build_space(context: GenerationContext) -> Space:
    return Space(**_base_kwargs(context))


def build_actor(context: GenerationContext) -> Actor:
    return Actor(**_base_kwargs(context))


def build_resource(context: GenerationContext) -> Resource:
    return Resource(**_base_kwargs(context))


def build_goal(context: GenerationContext) -> Goal:
    actor_id = str(
        context.metadata.get("actor_id") or context.context.get("actor_id") or ""
    )
    kind = str(context.metadata.get("kind") or context.context.get("kind") or "final")
    priority_val = context.metadata.get("priority")
    if priority_val is None:
        priority_val = context.context.get("priority")
    if priority_val is None:
        priority_val = 1.0
    priority = float(priority_val)
    status = str(
        context.metadata.get("status") or context.context.get("status") or "active"
    )
    horizon = dict(
        context.metadata.get("horizon") or context.context.get("horizon") or {}
    )
    target_condition = dict(
        context.metadata.get("target_condition")
        or context.context.get("target_condition")
        or {}
    )
    if not actor_id:
        raise ValueError(
            "Goal generation requires actor_id in context.metadata or context.context"
        )

    return Goal(
        **_base_kwargs(context),
        actor_id=actor_id,
        kind=kind,
        priority=priority,
        status=status,
        horizon=horizon,
        target_condition=target_condition,
    )


def build_strategy(context: GenerationContext) -> Strategy:
    actor_id = str(
        context.metadata.get("actor_id") or context.context.get("actor_id") or ""
    )
    root_node_id = str(
        context.metadata.get("root_node_id")
        or context.context.get("root_node_id")
        or "root"
    )
    goal_id_raw = context.metadata.get("goal_id") or context.context.get("goal_id")
    projection_policy = str(
        context.metadata.get("projection_policy")
        or context.context.get("projection_policy")
        or "perception_first"
    )
    action_id = str(
        context.metadata.get("action_id")
        or context.context.get("action_id")
        or f"action-{context.id}"
    )

    if not actor_id:
        raise ValueError(
            "Strategy generation requires actor_id in context.metadata or context.context"
        )

    node = StrategyNode(node_id=root_node_id, action_id=action_id)
    strategy = Strategy(
        **_base_kwargs(context),
        actor_id=actor_id,
        goal_id=str(goal_id_raw) if goal_id_raw else None,
        root_node_id=root_node_id,
        nodes=[node],
        projection_policy=projection_policy,
    )
    strategy.add_relation("action", action_id)
    return strategy


def build_action(context: GenerationContext) -> Action:
    actor_id = str(
        context.metadata.get("actor_id") or context.context.get("actor_id") or ""
    )
    world_id = str(
        context.metadata.get("world_id") or context.context.get("world_id") or ""
    )
    space_id = str(
        context.metadata.get("space_id") or context.context.get("space_id") or ""
    )
    action_type = str(
        context.metadata.get("action_type")
        or context.context.get("action_type")
        or "generic"
    )

    if not actor_id or not world_id or not space_id:
        raise ValueError(
            "Action generation requires actor_id, world_id, and space_id in metadata/context"
        )

    return Action(
        **_base_kwargs(context),
        actor_id=actor_id,
        world_id=world_id,
        space_id=space_id,
        action_type=action_type,
    )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _require_non_empty_string(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(
            f"Perception generation requires non-empty '{field_name}' in perceived_component_links"
        )
    return normalized


def build_perception(context: GenerationContext) -> Perception:
    actor_id = str(
        context.metadata.get("actor_id") or context.context.get("actor_id") or ""
    )
    source_id = str(
        context.metadata.get("source_id") or context.context.get("source_id") or ""
    )
    timestamp = context.metadata.get("timestamp", context.context.get("timestamp"))

    if not actor_id or not source_id:
        raise ValueError(
            "Perception generation requires actor_id and source_id in metadata/context"
        )

    raw_spaces = _as_mapping(
        context.metadata.get("perceived_spaces")
        or context.context.get("perceived_spaces")
    )
    perceived_spaces: dict[str, PerceivedSpace] = {}
    for space_id, payload in sorted(raw_spaces.items()):
        if isinstance(payload, PerceivedSpace):
            perceived_spaces[str(space_id)] = payload
            continue

        payload_map = _as_mapping(payload)
        raw_space = payload_map.get("space")
        if isinstance(raw_space, Space):
            space = raw_space
        elif isinstance(raw_space, Mapping):
            space = Space.from_dict(raw_space)
        else:
            space = Space(id=str(raw_space or space_id))

        perceived_spaces[str(space_id)] = PerceivedSpace(
            space=space,
            epistemic_status=str(payload_map.get("epistemic_status") or "certain"),
            noise_metadata=dict(payload_map.get("noise_metadata") or {}),
        )

    raw_memberships = (
        context.metadata.get("perceived_memberships")
        or context.context.get("perceived_memberships")
        or []
    )
    perceived_memberships: list[PerceivedMembership] = []
    for payload in raw_memberships:
        if isinstance(payload, PerceivedMembership):
            perceived_memberships.append(payload)
            continue

        payload_map = _as_mapping(payload)
        raw_membership = payload_map.get("membership")
        if isinstance(raw_membership, SpaceObjectMembership):
            membership = raw_membership
        else:
            membership_map = _as_mapping(raw_membership)
            membership = SpaceObjectMembership.from_dict(membership_map)

        perceived_memberships.append(
            PerceivedMembership(
                membership=membership,
                epistemic_status=str(payload_map.get("epistemic_status") or "certain"),
                noise_metadata=dict(payload_map.get("noise_metadata") or {}),
            )
        )

    raw_relations = (
        context.metadata.get("perceived_relations")
        or context.context.get("perceived_relations")
        or []
    )
    perceived_relations: list[PerceivedRelation] = []
    for payload in raw_relations:
        if isinstance(payload, PerceivedRelation):
            perceived_relations.append(payload)
            continue

        payload_map = _as_mapping(payload)
        raw_relation = payload_map.get("relation")
        if isinstance(raw_relation, SpaceRelation):
            relation = raw_relation
        else:
            relation_map = _as_mapping(raw_relation)
            relation = SpaceRelation.from_dict(relation_map)

        perceived_relations.append(
            PerceivedRelation(
                relation=relation,
                epistemic_status=str(payload_map.get("epistemic_status") or "certain"),
                noise_metadata=dict(payload_map.get("noise_metadata") or {}),
            )
        )

    raw_component_links = (
        context.metadata.get("perceived_component_links")
        or context.context.get("perceived_component_links")
        or []
    )
    perceived_component_links: list[PerceivedComponentLink] = []
    for payload in raw_component_links:
        if isinstance(payload, PerceivedComponentLink):
            perceived_component_links.append(payload)
            continue

        payload_map = _as_mapping(payload)
        perceived_component_links.append(
            PerceivedComponentLink(
                link_id=_require_non_empty_string(
                    payload_map.get("link_id"), "link_id"
                ),
                composite_id=_require_non_empty_string(
                    payload_map.get("composite_id"),
                    "composite_id",
                ),
                component_id=_require_non_empty_string(
                    payload_map.get("component_id"),
                    "component_id",
                ),
                epistemic_status=str(payload_map.get("epistemic_status") or "certain"),
                noise_metadata=dict(payload_map.get("noise_metadata") or {}),
            )
        )

    return Perception(
        id=context.id,
        actor_id=actor_id,
        source_id=source_id,
        schema_version="1.0",
        timestamp=timestamp,
        perceived_spaces=perceived_spaces,
        perceived_memberships=perceived_memberships,
        perceived_relations=perceived_relations,
        perceived_component_links=perceived_component_links,
        context=context.merged_context(),
        provenance=dict(context.provenance),
    )


def build_world(context: GenerationContext) -> World:
    world = World(
        id=context.id,
        attributes=context.merged_attributes(),
        relations=context.normalized_relations(),
        state=dict(context.state),
        context=context.merged_context(),
        provenance=dict(context.provenance),
    )

    for space_context in context.spaces:
        world.add_space(build_space(space_context))

    for actor_context in context.actors:
        world.register_object(build_actor(actor_context))

    for resource_context in context.resources:
        world.register_object(build_resource(resource_context))

    for placement in context.placements:
        world.place_object(placement.object_id, placement.space_id, role=placement.role)

    return world


def build_from_context(context: GenerationContext) -> Any:
    kind = context.kind.lower().strip()
    if kind == "world":
        return build_world(context)
    if kind == "space":
        return build_space(context)
    if kind == "actor":
        return build_actor(context)
    if kind == "resource":
        return build_resource(context)
    if kind == "goal":
        return build_goal(context)
    if kind == "strategy":
        return build_strategy(context)
    if kind == "action":
        return build_action(context)
    if kind == "perception":
        return build_perception(context)
    raise ValueError(f"Unsupported generation kind: {context.kind}")
