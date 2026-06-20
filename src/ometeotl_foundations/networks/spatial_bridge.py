"""Optional spatial-network coupling.

This module is NOT exported from the networks ``__init__.py``; callers
must import it explicitly:

    from ometeotl_foundations.networks.spatial_bridge import build_proximity_network

This is the only file in ``ometeotl_foundations/networks/`` that imports
from ``ometeotl_foundations/spatial/``.  The networks layer itself has no
spatial dependency.

``build_proximity_network`` builds an ``AdjacencyNetworkSpace`` by comparing
all pairs of ``GeometricSpace`` objects and connecting those within
*max_distance* with the specified relation type.  The resulting
``AdjacencyNetworkSpace._relations`` (a ``SpaceRelationGraph``) is
consistent with the output of ``derive_space_relations()`` from the spatial
layer, since both use the same relation type names.
"""

from __future__ import annotations

from itertools import combinations
from typing import Callable, Iterable

from ometeotl_core.model.spaces import Space

from ometeotl_foundations.spatial.geometric_space import GeometricSpace

from .adjacency_network_space import AdjacencyNetworkSpace
from .graph_kind import UNDIRECTED_WEIGHTED, GraphSpec


def build_proximity_network(
    geometric_spaces: Iterable[GeometricSpace],
    network_space: Space,
    *,
    max_distance: float,
    relation_type: str = "adjacent_to",
    weight_fn: Callable[[float], float] = lambda d: d,
    graph_spec: GraphSpec = UNDIRECTED_WEIGHTED,
    skip_abstract: bool = True,
) -> AdjacencyNetworkSpace:
    """Build an AdjacencyNetworkSpace by connecting geometrically close spaces.

    Each :class:`~ometeotl_foundations.spatial.geometric_space.GeometricSpace`
    becomes a node (keyed by ``space.id``).  Any pair whose geometry
    ``distance()`` is at or below *max_distance* receives a connection via
    ``add_connection()``, which populates ``_relations`` through
    ``SpaceRelationGraph.add_relation()`` with full constraint enforcement.

    The result's ``.relations`` property is a valid ``SpaceRelationGraph``
    consistent with the spatial ``derive_space_relations()`` output.

    Args:
        geometric_spaces: Iterable of GeometricSpace objects to process.
        network_space: The Space object that represents this network.
        max_distance: Maximum geometry distance for two spaces to be
            connected.  Pairs whose distance exceeds this threshold are
            not connected.  Use 0.0 to connect only touching/overlapping
            spaces.
        relation_type: SpaceRelationType name for added connections.
            Defaults to ``"adjacent_to"``.
        weight_fn: Maps the raw distance to an edge weight stored in the
            network metadata annotation.  Defaults to the identity
            (weight == distance).  Weights are stored as ``metadata`` on
            the connection if the relation type supports metadata; they
            are not enforced by the Graph Protocol.
        graph_spec: GraphSpec descriptor for the resulting network.
            Defaults to ``UNDIRECTED_WEIGHTED``.
        skip_abstract: If True (default), abstract GeometricSpaces are
            excluded from node registration and proximity comparisons.

    Returns:
        A new ``AdjacencyNetworkSpace`` whose ``_relations`` is populated
        with connections for all pairs within *max_distance*.
    """
    if max_distance < 0:
        raise ValueError(
            f"build_proximity_network: max_distance must be non-negative, got {max_distance}"
        )
    spaces_list = [
        gs for gs in geometric_spaces if not (skip_abstract and gs.is_abstract)
    ]

    net = AdjacencyNetworkSpace(space=network_space, graph_spec=graph_spec)

    # Register all nodes so isolated spaces appear in nodes().
    for gs in spaces_list:
        net.add_node(gs.id)

    # Connect pairs within max_distance.
    for gs_a, gs_b in combinations(spaces_list, 2):
        dist = gs_a.geometry.distance(gs_b.geometry)  # type: ignore[union-attr]
        if dist <= max_distance:
            weight = weight_fn(dist)
            net.add_connection(
                gs_a.id,
                gs_b.id,
                relation_type,
                metadata={"weight": weight, "distance": dist},
            )

    return net
