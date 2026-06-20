"""GraphBackend Protocol: adapter factory interface.

An adapter (e.g. ``ometeotl_adapters.networks_networkx``) implements this
protocol to provide library-backed graph construction.  The foundations
layer itself does not provide a concrete backend; ``AdjacencyGraph`` is
the pure-Python fallback graph.
"""

from __future__ import annotations

from typing import List, Protocol, Tuple, runtime_checkable

from .adjacency_graph import AdjacencyGraph
from .graph import Graph, NodeId


@runtime_checkable
class GraphBackend(Protocol):
    """Factory interface that adapter backends must satisfy.

    All factory methods return objects implementing the
    :class:`~ometeotl_foundations.networks.graph.Graph` protocol.
    """

    def make_graph(self, directed: bool = False) -> Graph:
        """Create an empty graph."""
        ...

    def make_from_edges(
        self,
        edges: List[Tuple[NodeId, NodeId, float]],
        directed: bool = False,
    ) -> Graph:
        """Create a graph from a list of ``(source, target, weight)`` triples."""
        ...

    def make_from_adjacency(self, adj: AdjacencyGraph) -> Graph:
        """Create a backend-native graph from an ``AdjacencyGraph``.

        This is the primary conversion path when the caller has built a
        graph at the foundations layer and wants to hand it to an
        adapter for rich algorithmic use (shortest path, centrality, …).
        """
        ...
