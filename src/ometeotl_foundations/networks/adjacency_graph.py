"""AdjacencyGraph: standalone pure-Python mutable graph.

Satisfies the :class:`~ometeotl_foundations.networks.graph.Graph` Protocol.
Used as the backing type for ``NetworkSpace[AdjacencyGraph]`` when a
simple generic graph is needed independently of a Space (e.g. intermediate
computation, adapter input via ``GraphBackend.make_from_adjacency``).

Design notes:
- Not coupled to SpaceRelationGraph or any Space concept.
- Undirected graphs canonicalize edges as (min_id, max_id); directed
  graphs preserve the given direction.
- Weights default to 1.0; callers may store arbitrary floats.
- Node metadata is stored separately from edge data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .graph import Graph, NodeId, JsonMap


@dataclass
class AdjacencyGraph:
    """Pure-Python mutable graph satisfying the Graph Protocol.

    Attributes:
        _directed: Whether edges are ordered (directed).  Set at construction
            time via ``directed=True``; cannot be changed after creation.
        _adj: Adjacency dict mapping ``source_id → {target_id → weight}``.
        _node_meta: Per-node metadata dicts.
    """

    _directed: bool = field(default=False)
    _adj: Dict[NodeId, Dict[NodeId, float]] = field(
        init=False, repr=False, default_factory=dict
    )
    _node_meta: Dict[NodeId, Dict[str, Any]] = field(
        init=False, repr=False, default_factory=dict
    )

    @classmethod
    def create(
        cls,
        directed: bool = False,
    ) -> "AdjacencyGraph":
        """Named constructor — cleaner than relying on the private ``_directed`` arg."""
        g = cls(_directed=directed)
        return g

    # ------------------------------------------------------------------
    # Graph Protocol — structural properties
    # ------------------------------------------------------------------

    @property
    def is_directed(self) -> bool:
        return self._directed

    @property
    def node_count(self) -> int:
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        if self._directed:
            return sum(len(nbrs) for nbrs in self._adj.values())
        # Each canonical undirected edge is stored once (u→v with u<=v).
        # Count from the node that is lexicographically smaller or equal.
        return sum(
            sum(1 for v in nbrs if node_id <= v) for node_id, nbrs in self._adj.items()
        )

    # ------------------------------------------------------------------
    # Graph Protocol — query methods
    # ------------------------------------------------------------------

    def nodes(self) -> List[NodeId]:
        return sorted(self._adj.keys())

    def edges(self) -> List[Tuple[NodeId, NodeId]]:
        result: List[Tuple[NodeId, NodeId]] = []
        for u, nbrs in self._adj.items():
            for v in nbrs:
                if self._directed or u <= v:
                    result.append((u, v))
        return sorted(result)

    def has_node(self, node_id: NodeId) -> bool:
        return node_id in self._adj

    def has_edge(self, source: NodeId, target: NodeId) -> bool:
        if self._directed:
            return target in self._adj.get(source, {})
        u, v = (source, target) if source <= target else (target, source)
        return v in self._adj.get(u, {})

    def neighbors(self, node_id: NodeId) -> List[NodeId]:
        """Return sorted out-neighbours (directed) or all neighbours (undirected)."""
        if self._directed:
            return sorted(self._adj.get(node_id, {}).keys())
        # Undirected: collect from both directions.
        nbrs: set[NodeId] = set()
        for v in self._adj.get(node_id, {}):
            nbrs.add(v)
        for candidate, nbr_dict in self._adj.items():
            if node_id in nbr_dict and candidate != node_id:
                nbrs.add(candidate)
        return sorted(nbrs)

    def degree(self, node_id: NodeId) -> int:
        """Return out-degree (directed) or total degree (undirected)."""
        return len(self.neighbors(node_id))

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(
        self, node_id: NodeId, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register *node_id*; idempotent if already present."""
        if node_id not in self._adj:
            self._adj[node_id] = {}
        if metadata is not None:
            self._node_meta[node_id] = dict(metadata)

    def remove_node(self, node_id: NodeId) -> None:
        """Remove *node_id* and all its incident edges; no-op if absent."""
        if node_id not in self._adj:
            return
        del self._adj[node_id]
        self._node_meta.pop(node_id, None)
        # Remove all edges pointing to node_id.
        for nbrs in self._adj.values():
            nbrs.pop(node_id, None)

    def add_edge(
        self,
        source: NodeId,
        target: NodeId,
        weight: float = 1.0,
    ) -> None:
        """Add an edge; auto-creates nodes if absent.

        Undirected graphs store the canonical form (``u≤v``).
        """
        self.add_node(source)
        self.add_node(target)
        if self._directed:
            self._adj[source][target] = weight
        else:
            u, v = (source, target) if source <= target else (target, source)
            self._adj[u][v] = weight

    def remove_edge(self, source: NodeId, target: NodeId) -> None:
        """Remove an edge; no-op if not present."""
        if self._directed:
            self._adj.get(source, {}).pop(target, None)
        else:
            u, v = (source, target) if source <= target else (target, source)
            self._adj.get(u, {}).pop(v, None)

    # ------------------------------------------------------------------
    # Convenience (not on Graph Protocol)
    # ------------------------------------------------------------------

    def get_edge_weight(self, source: NodeId, target: NodeId) -> Optional[float]:
        """Return edge weight or None if the edge does not exist."""
        if self._directed:
            return self._adj.get(source, {}).get(target)
        u, v = (source, target) if source <= target else (target, source)
        return self._adj.get(u, {}).get(v)

    def get_node_metadata(self, node_id: NodeId) -> Dict[str, Any]:
        """Return a copy of node metadata dict (empty if none set)."""
        return dict(self._node_meta.get(node_id, {}))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        return {
            "type": "adjacency_graph",
            "directed": self._directed,
            "nodes": {nid: dict(meta) for nid, meta in self._node_meta.items()},
            "edges": [
                [u, v, self._adj[u][v]]
                for u, nbrs in sorted(self._adj.items())
                for v in sorted(nbrs)
                if self._directed or u <= v
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AdjacencyGraph":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises:
            ValueError: If the ``"type"`` discriminator is wrong or required
                keys are missing.
        """
        if data.get("type") != "adjacency_graph":
            raise ValueError(
                f"AdjacencyGraph.from_dict: expected type 'adjacency_graph',"
                f" got {data.get('type')!r}"
            )
        g = cls(_directed=bool(data.get("directed", False)))
        for node_id, meta in (data.get("nodes") or {}).items():
            g.add_node(str(node_id), metadata=dict(meta) if meta else None)
        for entry in data.get("edges") or []:
            u, v, w = str(entry[0]), str(entry[1]), float(entry[2])
            g.add_edge(u, v, weight=w)
        return g


# Conformance assertion — fails at import time if the Protocol is broken.
assert isinstance(
    AdjacencyGraph(), Graph
), "AdjacencyGraph does not satisfy the Graph Protocol"
