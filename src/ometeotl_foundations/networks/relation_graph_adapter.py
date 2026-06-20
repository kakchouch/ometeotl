"""SpaceRelationGraphAdapter: read-only Graph Protocol view of a SpaceRelationGraph.

Bridges :class:`~ometeotl_core.model.space_relations.SpaceRelationGraph`
to the :class:`~ometeotl_foundations.networks.graph.Graph` Protocol so
that ``AdjacencyNetworkSpace`` (and any other consumer of a
``SpaceRelationGraph``) can be passed to functions that expect a ``Graph``.

Design notes:
- Read-only: this adapter exposes no mutation API.  Mutation goes through
  the owning ``AdjacencyNetworkSpace.add_connection`` / ``remove_connection``,
  which delegate to ``SpaceRelationGraph.add_relation`` / ``remove_relation``.
- Filters to a single ``relation_type`` so the directed/undirected semantics
  are unambiguous (each relation type has its own directedness).
- ``is_directed`` is derived from ``SPACE_RELATION_TYPES``:
    - symmetric types (adjacent_to, intersects_with) → undirected
    - antisymmetric types (contains_space) → directed
    - unknown custom types → directed (safe default)
- ``_node_ids`` carries the explicitly registered nodes from the owning
  ``AdjacencyNetworkSpace``, allowing isolated nodes to appear in ``nodes()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Tuple

from ometeotl_core.model.space_relations import SPACE_RELATION_TYPES, SpaceRelationGraph

from .graph import Graph, JsonMap, NodeId


@dataclass
class SpaceRelationGraphAdapter:
    """Read-only Graph Protocol view of a SpaceRelationGraph filtered to one relation type.

    Attributes:
        _relation_graph: The backing SpaceRelationGraph.
        _node_ids: Explicitly registered node IDs from the owning
            AdjacencyNetworkSpace (includes isolated nodes that have no
            relations yet).
        _relation_type: The relation type to filter edges by.
    """

    _relation_graph: SpaceRelationGraph
    _node_ids: FrozenSet[NodeId] = field(default_factory=frozenset)
    _relation_type: str = field(default="adjacent_to")

    # ------------------------------------------------------------------
    # Graph Protocol — structural properties
    # ------------------------------------------------------------------

    @property
    def is_directed(self) -> bool:
        rel_def = SPACE_RELATION_TYPES.get(self._relation_type)
        if rel_def is None:
            return True  # Unknown type → directed by default (safe)
        return not rel_def.is_symmetric

    @property
    def node_count(self) -> int:
        return len(self.nodes())

    @property
    def edge_count(self) -> int:
        return len(self.edges())

    # ------------------------------------------------------------------
    # Graph Protocol — query methods
    # ------------------------------------------------------------------

    def nodes(self) -> List[NodeId]:
        """Sorted union of explicitly registered node IDs and IDs in filtered relations."""
        ids: set[NodeId] = set(self._node_ids)
        for r in self._relation_graph.relations:
            if r.relation_type == self._relation_type:
                ids.add(r.source_space_id)
                ids.add(r.target_space_id)
        return sorted(ids)

    def edges(self) -> List[Tuple[NodeId, NodeId]]:
        result = [
            (r.source_space_id, r.target_space_id)
            for r in self._relation_graph.relations
            if r.relation_type == self._relation_type
        ]
        return sorted(result)

    def has_node(self, node_id: NodeId) -> bool:
        if node_id in self._node_ids:
            return True
        for r in self._relation_graph.relations:
            if r.relation_type == self._relation_type and (
                r.source_space_id == node_id or r.target_space_id == node_id
            ):
                return True
        return False

    def has_edge(self, source: NodeId, target: NodeId) -> bool:
        """O(1) via SpaceRelationGraph._relation_keys."""
        from ometeotl_core.model.space_relations import SpaceRelation

        canonical = SpaceRelation(
            source_space_id=source,
            target_space_id=target,
            relation_type=self._relation_type,
        ).canonicalize()
        key = (
            canonical.source_space_id,
            canonical.target_space_id,
            canonical.relation_type,
        )
        return key in self._relation_graph._relation_keys

    def neighbors(self, node_id: NodeId) -> List[NodeId]:
        """For symmetric (undirected) types returns all adjacent IDs.
        For directed types returns out-neighbours only."""
        rel_def = SPACE_RELATION_TYPES.get(self._relation_type)
        is_symmetric = rel_def.is_symmetric if rel_def else False

        nbrs: set[NodeId] = set()
        for r in self._relation_graph.relations:
            if r.relation_type != self._relation_type:
                continue
            if r.source_space_id == node_id:
                nbrs.add(r.target_space_id)
            elif is_symmetric and r.target_space_id == node_id:
                nbrs.add(r.source_space_id)
        return sorted(nbrs)

    def degree(self, node_id: NodeId) -> int:
        return len(self.neighbors(node_id))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        return {
            "type": "relation_graph_adapter",
            "relation_type": self._relation_type,
            "is_directed": self.is_directed,
            "node_ids": sorted(self._node_ids),
            "edges": [list(e) for e in self.edges()],
        }


# Conformance assertion — fails at import time if the Protocol is broken.
assert isinstance(
    SpaceRelationGraphAdapter(SpaceRelationGraph()),
    Graph,
), "SpaceRelationGraphAdapter does not satisfy the Graph Protocol"
