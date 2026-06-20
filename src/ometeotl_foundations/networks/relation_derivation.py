"""derive_space_relations_from_network: bridge from NetworkSpace to SpaceRelationGraph.

This function converts a ``NetworkSpace[G]`` to a ``SpaceRelationGraph``
by iterating the graph's edges and adding the corresponding
``SpaceRelation`` objects with the given ``edge_relation_type``.

For ``AdjacencyNetworkSpace``, the SpaceRelationGraph is already the
canonical source of truth and is accessible directly via ``.relations``.
Use this function when:
  1. You have a ``NetworkSpace[G]`` from an adapter (e.g. NetworkX) and
     need to bring its topology into the ometeotl_core world model.
  2. You have an ``AdjacencyNetworkSpace`` and want to extract a filtered
     view (specific relation type) as a new SpaceRelationGraph via
     ``ns.to_network_space(relation_type)``.

Design notes:
- No isinstance checks — pure Graph Protocol usage via ``.graph.edges()``.
- ``SpaceRelationGraph.add_relation()`` enforces all core constraints
  (canonicalization, antisymmetry, self-loops) so this function does not
  need to duplicate that logic.
- Self-loops in the source graph are skipped: non-reflexive relation
  types would raise from ``add_relation()`` anyway, and reflexive ones
  are not in SPACE_RELATION_TYPES.
- Abstract networks are excluded by default (``skip_abstract=True``),
  matching the convention in ``derive_space_relations`` in the spatial layer.
"""

from __future__ import annotations

from typing import TypeVar

from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph

from .network_space import NetworkSpace

G = TypeVar("G")


def derive_space_relations_from_network(
    network_space: "NetworkSpace[G]",
    *,
    edge_relation_type: str = "adjacent_to",
    skip_abstract: bool = True,
) -> SpaceRelationGraph:
    """Derive a SpaceRelationGraph from a NetworkSpace[G].

    Works for any ``G`` satisfying the ``Graph`` Protocol by iterating
    ``network_space.graph.edges()``.  Each edge becomes a ``SpaceRelation``
    with the given *edge_relation_type*.

    For ``AdjacencyNetworkSpace``, prefer direct access via ``.relations``
    (zero-copy, all relation types).  Call ``.to_network_space(relation_type)``
    first if you want to use this function to extract a specific relation type.

    Args:
        network_space: A ``NetworkSpace[G]`` instance.  Must have
            ``.is_abstract`` and ``.graph`` (a ``Graph`` Protocol object).
        edge_relation_type: The ``SpaceRelationType`` name to use for all
            edges.  Must be a key in ``SPACE_RELATION_TYPES``.
        skip_abstract: If True (default) and ``network_space.is_abstract``
            is True, return an empty ``SpaceRelationGraph`` without processing
            any edges.

    Returns:
        A new ``SpaceRelationGraph`` containing one relation per edge
        (self-loops excluded).

    Raises:
        ValueError: If *edge_relation_type* is not a known relation type
            (propagated from ``SpaceRelationGraph.add_relation``).
    """
    if skip_abstract and network_space.is_abstract:
        return SpaceRelationGraph()

    result = SpaceRelationGraph()
    for source, target in network_space.graph.edges():
        if source == target:
            continue
        result.add_relation(
            SpaceRelation(
                source_space_id=source,
                target_space_id=target,
                relation_type=edge_relation_type,
            )
        )
    return result
