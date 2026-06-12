"""derive_space_relations: derive SpaceRelationGraph from GeometricSpace objects.

This function is the primary bridge between the spatial foundations layer
and ometeotl_core.  Given a collection of GeometricSpace objects, it
compares their geometries pairwise and populates a SpaceRelationGraph
with the resulting topological relations (containment, intersection,
adjacency), enforcing all algebraic constraints defined in core.

Design notes:
- Containment is checked before intersection: if A contains B, they are
  not additionally recorded as intersecting.
- Adjacency (adjacent_to) is derived only when a positive
  ``adjacency_tolerance`` is given and no containment or intersection
  relation was detected.
- When two geometries have different concrete types, comparison falls
  back to their ``.bounds`` (both always return BoundingBox).  This is
  documented in the function docstring.
- ``skip_abstract=True`` (default) automatically excludes spaces where
  ``space.is_abstract`` is True, matching the semantic intent of
  abstract spaces as conceptual groupings.
- The caller controls which spaces are included; passing a subset is
  valid and the resulting graph will be partial.
"""

from __future__ import annotations

from typing import Iterable, List

from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph

from .bounding_box import BoundingBox
from .geometric_space import GeometricSpace
from .geometry import Geometry


def _safe_contains(a: Geometry, b: Geometry) -> bool:
    """Contains check with BoundingBox fallback on type mismatch."""
    if type(a) is type(b):
        return a.contains(b)
    return a.bounds.contains(b.bounds)


def _safe_intersects(a: Geometry, b: Geometry) -> bool:
    """Intersects check with BoundingBox fallback on type mismatch."""
    if type(a) is type(b):
        return a.intersects(b)
    return a.bounds.intersects(b.bounds)


def _safe_distance(a: Geometry, b: Geometry) -> float:
    """Distance check with BoundingBox fallback on type mismatch."""
    if type(a) is type(b):
        return a.distance(b)
    return a.bounds.distance(b.bounds)


def derive_space_relations(
    spaces: Iterable[GeometricSpace],
    *,
    skip_abstract: bool = True,
    adjacency_tolerance: float = 0.0,
    derive_containment: bool = True,
    derive_intersection: bool = True,
    derive_adjacency: bool = True,
) -> SpaceRelationGraph:
    """Derive a SpaceRelationGraph from the geometries of GeometricSpace objects.

    For each unordered pair (A, B) of spaces the function attempts to
    classify their relationship in priority order:

    1. **contains_space** (A contains B): if ``derive_containment`` and
       ``A.geometry.contains(B.geometry)``.
    2. **contains_space** (B contains A): symmetric containment check.
    3. **intersects_with**: if ``derive_intersection`` and the geometries
       share interior area (and neither contains the other).
    4. **adjacent_to**: if ``derive_adjacency`` and
       ``distance(A, B) <= adjacency_tolerance`` (with the default of
       0.0, only touching boundaries qualify).

    Args:
        spaces: GeometricSpace objects to include.  The caller decides
            which spaces to pass; the resulting graph is partial if only
            a subset is given.
        skip_abstract: When True (default), spaces where
            ``space.is_abstract`` is True are silently excluded.
        adjacency_tolerance: Maximum distance (in the geometry's native
            units) at which two non-overlapping spaces are considered
            adjacent.  Set to 0.0 to require exact boundary contact.
            Units are those of the respective coordinate systems — no
            conversion is performed.
        derive_containment: Include ``contains_space`` relations.
        derive_intersection: Include ``intersects_with`` relations.
        derive_adjacency: Include ``adjacent_to`` relations.

    Returns:
        A :class:`~ometeotl_core.model.space_relations.SpaceRelationGraph`
        populated with the derived relations.  All algebraic constraints
        defined in core (antisymmetry, no self-loops) are enforced by
        ``SpaceRelationGraph.add_relation``.

    Note on mixed geometry types:
        When two geometries have different concrete types the comparison
        falls back to their axis-aligned bounding boxes (``.bounds``),
        which always returns a BoundingBox.  Results are therefore
        approximations in that case.
    """
    filtered: List[GeometricSpace] = [
        gs for gs in spaces if not (skip_abstract and gs.is_abstract)
    ]

    graph = SpaceRelationGraph()

    for i, gs_a in enumerate(filtered):
        geom_a: Geometry = gs_a.geometry  # type: ignore[assignment]

        for gs_b in filtered[i + 1 :]:
            geom_b: Geometry = gs_b.geometry  # type: ignore[assignment]

            if derive_containment and _safe_contains(geom_a, geom_b):
                graph.add_relation(
                    SpaceRelation(
                        source_space_id=gs_a.id,
                        target_space_id=gs_b.id,
                        relation_type="contains_space",
                    )
                )
                continue

            if derive_containment and _safe_contains(geom_b, geom_a):
                graph.add_relation(
                    SpaceRelation(
                        source_space_id=gs_b.id,
                        target_space_id=gs_a.id,
                        relation_type="contains_space",
                    )
                )
                continue

            if derive_intersection and _safe_intersects(geom_a, geom_b):
                graph.add_relation(
                    SpaceRelation(
                        source_space_id=gs_a.id,
                        target_space_id=gs_b.id,
                        relation_type="intersects_with",
                    )
                )
                continue

            if (
                derive_adjacency
                and _safe_distance(geom_a, geom_b) <= adjacency_tolerance
            ):
                graph.add_relation(
                    SpaceRelation(
                        source_space_id=gs_a.id,
                        target_space_id=gs_b.id,
                        relation_type="adjacent_to",
                    )
                )

    return graph
