"""Perception layer for limited-visibility multi-agent simulation (Lab 7).

Responsibilities:
- FactionCoverageRule: determines which spaces are visible to a faction
  (owned spaces + immediate neighbors only)
- get_faction_perception: builds a Sensor and returns a Perception
  for a given faction in the current game state
- visible_border_targets: extracts unowned neighbor node IDs from a perception
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ometeotl_core.model.perception import Perception
from ometeotl_core.model.sensor import CoverageRule, Sensor

if TYPE_CHECKING:
    from .engine import SimState


class FactionCoverageRule(CoverageRule):
    """Coverage rule that includes only spaces owned by a faction or adjacent to owned spaces.

    Parameters
    ----------
    faction_id : str
        The faction for which visibility is computed.
    owned_space_ids : set[str]
        Set of space IDs currently owned by this faction.
    neighbor_space_ids : set[str]
        Set of space IDs that are neighbors of owned spaces.
    """

    def __init__(
        self,
        faction_id: str,
        owned_space_ids: set[str],
        neighbor_space_ids: set[str],
    ):
        self.faction_id = faction_id
        self.owned_space_ids = owned_space_ids
        self.neighbor_space_ids = neighbor_space_ids
        # Visible set is union of owned + neighbors
        self.visible_space_ids = owned_space_ids | neighbor_space_ids

    def covers_space(self, space: Any, actor_id: str, world: Any) -> bool:
        """Return True if space is visible to this faction (owned or neighbor)."""
        return space.id in self.visible_space_ids

    def covers_membership(self, membership: Any, actor_id: str, world: Any) -> bool:
        """Return True if membership's space is visible to this faction."""
        return membership.space_id in self.visible_space_ids

    def covers_relation(self, relation: Any, actor_id: str, world: Any) -> bool:
        """Return True if relation connects two visible spaces.

        This filters out relations going to unseen parts of the map.
        """
        space_a_visible = relation.source_space_id in self.visible_space_ids
        space_b_visible = relation.target_space_id in self.visible_space_ids
        return space_a_visible and space_b_visible


def get_faction_perception(state: SimState, faction_id: str) -> Perception:
    """Build a faction-specific perception for the current game state.

    The perception includes only spaces owned by the faction or adjacent to
    owned spaces (fog-of-war with distance-1 visibility).

    Parameters
    ----------
    state : SimState
        Current simulation state.
    faction_id : str
        ID of the faction for which to build perception.

    Returns
    -------
    Perception
        A Perception object containing only visible spaces and relations.
    """
    # Collect owned and neighbor space IDs
    owned_space_ids = {
        nid for nid, node in state.nodes.items() if node.owner_id == faction_id
    }

    # Find neighbors of owned spaces using the relation graph
    neighbor_space_ids = set()
    for owned_id in owned_space_ids:
        # Query the SpaceRelationGraph for neighbors of this space
        neighbors = state.relation_graph.neighbors_of(owned_id)
        neighbor_space_ids.update(neighbors)

    # Remove the owned IDs from neighbors (they should only appear in owned_space_ids)
    neighbor_space_ids -= owned_space_ids

    # Create the coverage rule for this faction
    rule = FactionCoverageRule(faction_id, owned_space_ids, neighbor_space_ids)

    # Create a sensor with this rule and sense the world
    sensor = Sensor(coverage_rules=[rule])
    perception = sensor.sense(state.world, faction_id)

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
