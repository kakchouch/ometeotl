"""Perception layer for limited-visibility multi-agent simulation.

This module uses a lightweight Sensor path based on Ometeotl primitives.
It keeps the Sensor/CoverageRule architecture while overriding expensive
deep-copy internals that are not needed for this lab's real-time pacing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ometeotl_core.model.perception import (
    PerceivedComponentLink,
    PerceivedMembership,
    PerceivedRelation,
    PerceivedSpace,
    Perception,
)
from ometeotl_core.model.sensor import CoverageRule, Sensor
from ometeotl_core.model.space_relations import SpaceRelation
from ometeotl_core.model.spaces import Space, SpaceObjectMembership
from ometeotl_core.model.world import World

if TYPE_CHECKING:
    from .engine import SimState


def _visible_space_ids(state: SimState, faction_id: str) -> set[str]:
    owned_space_ids = {
        nid for nid, node in state.nodes.items() if node.owner_id == faction_id
    }
    neighbor_space_ids = set()
    for owned_id in owned_space_ids:
        neighbor_space_ids.update(state.relation_graph.neighbors_of(owned_id))
    return owned_space_ids | (neighbor_space_ids - owned_space_ids)


class FactionCoverageRule(CoverageRule):
    """Coverage rule: owned spaces + 1-hop neighboring spaces."""

    def __init__(self, visible_space_ids: set[str]):
        self.visible_space_ids = visible_space_ids

    def covers_space(self, space: Space, actor_id: str, world: World) -> bool:
        return space.id in self.visible_space_ids

    def covers_membership(
        self,
        membership: SpaceObjectMembership,
        actor_id: str,
        world: World,
    ) -> bool:
        return membership.space_id in self.visible_space_ids

    def covers_relation(
        self,
        relation: SpaceRelation,
        actor_id: str,
        world: World,
    ) -> bool:
        return (
            relation.source_space_id in self.visible_space_ids
            and relation.target_space_id in self.visible_space_ids
        )


class LightweightLabSensor(Sensor):
    """Fast Sensor implementation that avoids world deepcopy in hot paths."""

    def _sense_spaces(self, world: World, actor_id: str, perception: Perception) -> None:
        for space_id, _space in world.space_object_graph.spaces.items():
            # Build a compact perceived space payload rather than deep-copying full space state.
            space_stub = Space(id=space_id)
            space_stub.label = space_id
            if not self._covers_space(space_stub, actor_id, world):
                continue
            perception.perceived_spaces[space_id] = PerceivedSpace(
                space=space_stub,
                epistemic_status=self.default_epistemic_status,
                noise_metadata={},
            )

    def _sense_memberships(
        self,
        world: World,
        actor_id: str,
        perception: Perception,
    ) -> None:
        for membership in world.space_object_graph.object_memberships:
            if not self._covers_membership(membership, actor_id, world):
                continue
            perception.perceived_memberships.append(
                PerceivedMembership(
                    membership=SpaceObjectMembership(
                        object_id=membership.object_id,
                        space_id=membership.space_id,
                        role=membership.role,
                        validity=dict(membership.validity),
                        metadata=dict(membership.metadata),
                    ),
                    epistemic_status=self.default_epistemic_status,
                    noise_metadata={},
                )
            )

    def _sense_relations(
        self,
        world: World,
        actor_id: str,
        perception: Perception,
    ) -> None:
        for relation in world.space_relation_graph.relations:
            if relation.relation_type != "adjacent_to":
                continue
            if not self._covers_relation(relation, actor_id, world):
                continue
            rel_copy = SpaceRelation(
                source_space_id=relation.source_space_id,
                target_space_id=relation.target_space_id,
                relation_type=relation.relation_type,
            )
            perception.perceived_relations.append(
                PerceivedRelation(
                    relation=rel_copy,
                    epistemic_status=self.default_epistemic_status,
                    noise_metadata={},
                )
            )


def get_faction_perception(state: SimState, faction_id: str) -> Perception:
    """Build a lightweight faction-specific perception via Sensor path."""
    visible_ids = _visible_space_ids(state, faction_id)
    sensor = LightweightLabSensor(
        coverage_rules=[FactionCoverageRule(visible_ids)],
        noise_rules=[],
        default_epistemic_status="certain",
    )
    perception = sensor.sense(state.world, faction_id, timestamp=state.tick)

    for faction in state.factions.values():
        for component_id in faction.get_components():
            if component_id not in visible_ids:
                continue
            link_id = f"component-{faction.faction_id}-{component_id}"
            perception.perceived_component_links.append(
                PerceivedComponentLink(
                    link_id=link_id,
                    composite_id=faction.faction_id,
                    component_id=component_id,
                )
            )

    return perception


def visible_border_targets(perception: Perception, owned_set: set[str]) -> list[str]:
    """Extract list of visible unowned neighbor node IDs from a perception.

    This helper queries the perception's relations to find edges from owned
    nodes to unowned neighbors.

    Parameters
    ----------
    perception : Perception
        The faction's perception (from get_faction_perception).
    owned_set : set[str]
        Set of node IDs owned by the faction.

    Returns
    -------
    list[str]
        List of visible unowned neighbor node IDs that the faction can attack.
    """
    targets = set()

    # Iterate through perceived relations to find edges going to unowned spaces
    for perceived_rel in perception.perceived_relations:
        rel = perceived_rel.relation
        # Check if this relation connects an owned space to an unowned space
        source_owned = rel.source_space_id in owned_set
        target_owned = rel.target_space_id in owned_set

        if source_owned and not target_owned:
            # Edge from owned to unowned: target is an unowned neighbor
            targets.add(rel.target_space_id)
        elif target_owned and not source_owned:
            # Edge from unowned to owned: source is an unowned neighbor
            targets.add(rel.source_space_id)

    return sorted(list(targets))
