---
title: "BoundingBox"
---

Source:
- [src/ometeotl_foundations/spatial/bounding_box.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/bounding_box.py)

Local role:
Pure-Python, frozen-dataclass implementation of the `Geometry` protocol. The only concrete geometry at the foundations layer — makes the spatial module fully usable without any adapter.

Big-picture role:
Used as the geometry type `G` for `GeometricSpace[BoundingBox]`, `SpatialExtent[BoundingBox]`, and `SpatialMap[BoundingBox]` when no adapter is installed. Adapter-backed geometry types must expose a `.bounds` property that returns a `BoundingBox`, enabling fallback comparisons.

## Fields

- `min_x: float` — left boundary
- `min_y: float` — bottom boundary
- `max_x: float` — right boundary
- `max_y: float` — top boundary

Raises `ValueError` on construction if `min_x > max_x` or `min_y > max_y`.

## Geometry protocol — properties

- `area -> float` — zero for degenerate (point or line) boxes
- `centroid -> Coordinate2D` — centre of the box
- `bounds -> BoundingBox` — returns `self`; a BoundingBox is its own AABB

## Geometry protocol — predicate methods

- `contains(other: Geometry) -> bool` — True if every point of `other` lies within or on the boundary of this box. Falls back to `other.bounds` for non-BoundingBox operands.
- `intersects(other: Geometry) -> bool` — True if the boxes share any common point (including boundary). Falls back to `other.bounds`.
- `touches(other: Geometry) -> bool` — DE-9IM semantics: at least one common point **and** open interiors are disjoint. Implemented as `not_disjoint AND NOT interior_overlap` using strict inequalities for interior overlap detection. Falls back to `other.bounds`.
- `distance(other: Geometry) -> float` — minimum Euclidean distance; 0.0 if they share any point. Falls back to `other.bounds`.

## Convenience methods (not on Geometry protocol)

- `contains_point(point: Coordinate2D) -> bool` — True if `point` lies inside or on the boundary
- `expand(margin: float) -> BoundingBox` — new box expanded by `margin` on every side
- `union(other: BoundingBox) -> BoundingBox` — smallest box that contains both

## Constructors

- `BoundingBox(min_x, min_y, max_x, max_y)` — standard constructor
- `@classmethod from_center(center: Coordinate2D, half_w, half_h) -> BoundingBox`
- `@classmethod from_point(point: Coordinate2D) -> BoundingBox` — degenerate zero-area box at a point

## Serialisation

- `to_dict() -> JsonMap` — `{"type": "bounding_box", "min_x": …, "min_y": …, "max_x": …, "max_y": …}`
- `@classmethod from_dict(data) -> BoundingBox` — raises `ValueError` if `"type"` discriminator does not match or required keys are missing

Example:

```python
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinates import Coordinate2D

city = BoundingBox(0, 0, 100, 80)
district = BoundingBox(10, 10, 40, 40)

assert city.contains(district)
assert city.area == 8000.0
assert city.centroid == Coordinate2D(50.0, 40.0)

# Touching but not overlapping
east = BoundingBox(100, 0, 200, 80)
assert city.touches(east)

# Round-trip serialisation
restored = BoundingBox.from_dict(city.to_dict())
assert restored == city

# From centre
box = BoundingBox.from_center(Coordinate2D(50, 40), half_w=10, half_h=5)
```

Notes:
- All predicate methods fall back to bounding-box comparison (`other.bounds`) when the operand is not a `BoundingBox`. Results are then approximations.
- Conformance to the `Geometry` protocol is asserted at import time: `assert isinstance(BoundingBox(0,0,1,1), Geometry)`.

See also:
- [Geometry Protocol](/ometeotl/documentation/class-reference/foundations/spatial/geometry/)
- [GeometricSpace](/ometeotl/documentation/class-reference/foundations/spatial/geometric-space/)
- [derive_space_relations](/ometeotl/documentation/class-reference/foundations/spatial/relation-derivation/)
