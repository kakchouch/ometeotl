"""Networks foundations layer: graph-theory specialization of ometeotl_core.

Public surface:

Vocabulary
----------
- :class:`GraphKind` — structural category enum
- :class:`GraphSpec` — frozen graph descriptor
- :data:`UNDIRECTED_SIMPLE`, :data:`DIRECTED_SIMPLE`,
  :data:`UNDIRECTED_WEIGHTED`, :data:`DIRECTED_WEIGHTED` — predefined singletons

Protocols
---------
- :class:`Graph` — runtime-checkable Protocol for all graph implementations
- :class:`GraphBackend` — runtime-checkable Protocol for adapter factories
- :data:`NodeId` — ``str`` type alias for node identifiers

Implementations
---------------
- :class:`AdjacencyGraph` — standalone pure-Python mutable graph
- :class:`SpaceRelationGraphAdapter` — read-only Graph view of a SpaceRelationGraph
- :class:`NetworkSpace` — frozen generic Space + graph (adapter extension point)
- :class:`AdjacencyNetworkSpace` — mutable Space + SpaceRelationGraph (foundations layer)
- :class:`NetworkExtent` — where an object sits in a network (at a node)
- :class:`NetworkMap` — mutable container mapping ObjectId → NetworkExtent

Bridge
------
- :func:`derive_space_relations_from_network` — derive SpaceRelationGraph from NetworkSpace[G]

Optional spatial coupling (not exported; explicit import required):
    from ometeotl_foundations.networks.spatial_bridge import build_proximity_network
"""

from .adjacency_graph import AdjacencyGraph
from .adjacency_network_space import AdjacencyNetworkSpace
from .graph import Graph, NodeId
from .graph_backend import GraphBackend
from .graph_kind import (
    DIRECTED_SIMPLE,
    DIRECTED_WEIGHTED,
    UNDIRECTED_SIMPLE,
    UNDIRECTED_WEIGHTED,
    GraphKind,
    GraphSpec,
)
from .network_extent import NetworkExtent
from .network_map import NetworkMap
from .network_space import NetworkSpace
from .relation_derivation import derive_space_relations_from_network
from .relation_graph_adapter import SpaceRelationGraphAdapter

__all__ = [
    # Vocabulary
    "NodeId",
    "GraphKind",
    "GraphSpec",
    "UNDIRECTED_SIMPLE",
    "DIRECTED_SIMPLE",
    "UNDIRECTED_WEIGHTED",
    "DIRECTED_WEIGHTED",
    # Protocols
    "Graph",
    "GraphBackend",
    # Implementations
    "AdjacencyGraph",
    "SpaceRelationGraphAdapter",
    "NetworkSpace",
    "AdjacencyNetworkSpace",
    "NetworkExtent",
    "NetworkMap",
    # Bridge
    "derive_space_relations_from_network",
    # spatial_bridge is intentionally omitted — explicit import only
]
