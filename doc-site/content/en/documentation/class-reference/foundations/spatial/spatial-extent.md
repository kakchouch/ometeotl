---
title: "SpatialExtent"
---

Source:
- [src/ometeotl_foundations/spatial/spatial_extent.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/spatial_extent.py)

Local role:
Frozen generic dataclass recording where a non-space object (actor, resource, etc.) is located within a named coordinate frame.

Big-picture role:
Distinct from `GeometricSpace`:
- **`GeometricSpace`** describes what shape a *space* IS.
- **`SpatialExtent`** describes where an *object* IS within a space.

`SpatialMap[G]` maps `ObjectId → SpatialExtent[G]` to track actor and resource positions.

## Type parameter

`G` — the concrete geometry type (e.g. `BoundingBox`). Must satisfy the `Geometry` protocol.

## Fields

- `space_id: ObjectId` — loose reference (by ID string) to the `GeometricSpace` that defines the coordinate frame; keeps `SpatialExtent` lightweight with no hard dependency on the space collection
- `geometry: G` — the object's footprint or position
- `coordinate_system: CoordinateSystem = CARTESIAN_2D` — coordinate frame of `geometry`
- `metadata: JsonMap = {}` — arbitrary key/value annotations

Frozen — mutations create a new `SpatialExtent`.

## Serialisation

- `to_dict() -> JsonMap` — self-contained; calls `geometry.to_dict()`
- `@classmethod from_dict(data, geometry_deserializer: Callable[[JsonMap], G]) -> SpatialExtent[G]` — injected deserializer pattern; pass `BoundingBox.from_dict` at the foundations layer

Example:

```python
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.spatial_extent import SpatialExtent
from ometeotl_foundations.spatial.coordinate_system import WGS84

actor_extent = SpatialExtent(
    space_id="district-1",
    geometry=BoundingBox(2.32, 48.83, 2.34, 48.85),
    coordinate_system=WGS84,
    metadata={"role": "patrol-zone"},
)

# Round-trip
d = actor_extent.to_dict()
restored = SpatialExtent.from_dict(d, BoundingBox.from_dict)
assert restored.space_id == actor_extent.space_id
```

See also:
- [GeometricSpace](/ometeotl/documentation/class-reference/foundations/spatial/geometric-space/) — space identity vs. object position
- [SpatialMap](/ometeotl/documentation/class-reference/foundations/spatial/spatial-map/) — container for extents
