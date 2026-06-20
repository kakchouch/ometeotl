"""Graph structural Protocol for the networks foundations layer.

All graph implementations — AdjacencyGraph (pure Python) and any
adapter-backed wrapper — must satisfy this protocol.

The ``to_dict`` method is part of the contract so that
:class:`~ometeotl_foundations.networks.network_space.NetworkSpace`
can serialise itself without knowing the concrete graph type.
Every dict produced by ``to_dict`` must include a ``"type"``
discriminator key so deserialisation can dispatch to the right
``from_dict`` implementation.

Path and traversal methods (shortest path, centrality, …) are
intentionally excluded — those belong in the adapter layer where
library-specific algorithms live.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable

JsonMap = Dict[str, Any]

#: Node identifiers are plain strings, matching ``ObjectId`` in ometeotl_core.
#: Nodes typically correspond to Space or ModelObject IDs.
NodeId = str


@runtime_checkable
class Graph(Protocol):
    """Contract for all graph objects in the networks foundations layer.

    ``runtime_checkable`` allows ``isinstance(obj, Graph)`` guards in
    protocol conformance assertions at import time.

    Implementations must be self-contained; mutation is the caller's
    concern (``AdjacencyGraph`` is mutable, adapter wrappers may be
    read-only views).
    """

    @property
    def is_directed(self) -> bool:
        """Whether edges are ordered (directed) or unordered (undirected)."""
        ...

    @property
    def node_count(self) -> int:
        """Total number of nodes in the graph."""
        ...

    @property
    def edge_count(self) -> int:
        """Total number of edges (undirected counts each pair once)."""
        ...

    def nodes(self) -> List[NodeId]:
        """Return all node IDs in sorted order."""
        ...

    def edges(self) -> List[Tuple[NodeId, NodeId]]:
        """Return all edges as (source, target) pairs in sorted order.

        For undirected graphs each edge appears once in canonical form
        (``u < v`` lexicographically).
        """
        ...

    def has_node(self, node_id: NodeId) -> bool:
        """Return True if *node_id* is present in the graph."""
        ...

    def has_edge(self, source: NodeId, target: NodeId) -> bool:
        """Return True if an edge from *source* to *target* exists."""
        ...

    def neighbors(self, node_id: NodeId) -> List[NodeId]:
        """Return sorted list of neighbours of *node_id*.

        For directed graphs returns out-neighbours only.
        """
        ...

    def degree(self, node_id: NodeId) -> int:
        """Return degree of *node_id*.

        For directed graphs returns out-degree.
        """
        ...

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict.

        The returned dict must include a ``"type"`` discriminator key
        (e.g. ``"adjacency_graph"``) so callers can dispatch to the
        correct ``from_dict`` implementation.
        """
        ...
