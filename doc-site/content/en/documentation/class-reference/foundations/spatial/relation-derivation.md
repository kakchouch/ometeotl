---
title: "derive_space_relations"
---

Source:
- [src/ometeotl_foundations/spatial/relation_derivation.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/relation_derivation.py)

Local role:
Bridge function from the spatial foundations layer back to `ometeotl_core`. Compares geometries pairwise and populates a `SpaceRelationGraph` with the resulting topological relations.

Big-picture role:
Closes the loop from concrete geometry back to the abstract core model. The caller passes `GeometricSpace` objects (which carry both `space.id` and `geometry`) and receives a `SpaceRelationGraph` ready for use in world-level reasoning.

## Signature

```python
def derive_space_relations(
    spaces: Iterable[GeometricSpace],
    *,
    skip_abstract: bool = True,
    adjacency_tolerance: float = 0.0,
    derive_containment: bool = True,
    derive_intersection: bool = True,
    derive_adjacency: bool = True,
) -> SpaceRelationGraph:
```

## Algorithm

For each unordered pair (A, B) the function checks in priority order:

1. **contains_space** (A contains B) — if `derive_containment` and `A.geometry.contains(B.geometry)`
2. **contains_space** (B contains A) — symmetric containment check
3. **intersects_with** — if `derive_intersection` and geometries share interior area (and neither contains the other)
4. **adjacent_to** — if `derive_adjacency` and `distance(A, B) <= adjacency_tolerance`

Only the first matching relation is recorded per pair; the `continue` after each match prevents double-classification.

## Parameters

- `spaces` — `GeometricSpace` objects to include; the resulting graph is partial if only a subset is passed
- `skip_abstract: bool = True` — when `True`, spaces where `space.is_abstract` is `True` are silently excluded
- `adjacency_tolerance: float = 0.0` — maximum distance (in native units) at which two non-overlapping spaces are considered adjacent; `0.0` requires exact boundary contact
- `derive_containment`, `derive_intersection`, `derive_adjacency: bool = True` — per-relation-type flags to enable/disable entire classes of derivation

## Mixed geometry types

When two geometries have different concrete types, comparisons fall back to their axis-aligned bounding boxes (`.bounds`, always a `BoundingBox`). Results are approximations in that case.

## Returns

A `SpaceRelationGraph` populated with the derived relations. All algebraic constraints from core (antisymmetry, no self-loops) are enforced by `SpaceRelationGraph.add_relation`.

Example:

```python
from ometeotl_core.model.spaces import Space
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.geometric_space import GeometricSpace
from ometeotl_foundations.spatial.relation_derivation import derive_space_relations

def make_gs(sid, box):
    s = Space(id=sid)
    return GeometricSpace(space=s, geometry=box)

region   = make_gs("region",   BoundingBox(0,  0,  100, 100))
district = make_gs("district", BoundingBox(10, 10, 40,  40))   # inside region
city     = make_gs("city",     BoundingBox(200, 0, 300, 100))   # disjoint

graph = derive_space_relations([region, district, city])

# region contains district
from ometeotl_core.model.space_relations import SpaceRelationGraph
rels = graph.relations_from("region")
assert any(r.relation_type == "contains_space" and r.target_space_id == "district" for r in rels)

# city is disjoint from both — no relation recorded
assert graph.relations_from("city") == []
```

See also:
- [GeometricSpace](/ometeotl/documentation/class-reference/foundations/spatial/geometric-space/)
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- [BoundingBox](/ometeotl/documentation/class-reference/foundations/spatial/bounding-box/)
