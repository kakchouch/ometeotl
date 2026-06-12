---
title: "Geometry Protocol"
---

Source:
- [src/ometeotl_foundations/spatial/geometry.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/geometry.py)

Local role:
Structural `Protocol` (PEP 544) that all geometry implementations must satisfy. Decorated with `@runtime_checkable` so `isinstance(obj, Geometry)` guards work at runtime.

Big-picture role:
The contract between the spatial foundations layer and adapter backends. `BoundingBox` satisfies it at the foundations layer; the Shapely adapter will wrap `shapely.geometry.*` objects in a thin class that also satisfies it.

## Protocol members

Properties:
- `area -> float` — area in the native units of the coordinate system; 0 for point/line geometries
- `centroid -> Coordinate2D` — geometric centroid as a 2-D coordinate
- `bounds -> BoundingBox` — axis-aligned bounding box of the geometry

Methods:
- `contains(other: Geometry) -> bool` — True if this geometry fully contains `other`
- `intersects(other: Geometry) -> bool` — True if they share any interior area
- `touches(other: Geometry) -> bool` — True if they share a boundary but their open interiors are disjoint (DE-9IM semantics)
- `distance(other: Geometry) -> float` — minimum distance; 0.0 if they overlap
- `to_dict() -> JsonMap` — serialise to a plain dict; the dict **must** include a `"type"` discriminator key (e.g. `"bounding_box"`) so downstream callers can dispatch to the correct `from_dict`

## Design notes

- Mutation (union, buffer) is intentionally **not** on the protocol — those are construction operations handled by `SpatialBackend`.
- `TYPE_CHECKING`-only import of `BoundingBox` avoids a circular import with `bounding_box.py`.
- `BoundingBox` satisfies this protocol and its conformance is asserted at import time.

Example:

```python
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.geometry import Geometry

box = BoundingBox(0, 0, 10, 10)
assert isinstance(box, Geometry)   # runtime_checkable

# Any object with the right attributes/methods satisfies the protocol
```

See also:
- [BoundingBox](/ometeotl/documentation/class-reference/foundations/spatial/bounding-box/) — concrete implementation
- [SpatialBackend](/ometeotl/documentation/class-reference/foundations/spatial/spatial-backend/) — factory for geometry objects
