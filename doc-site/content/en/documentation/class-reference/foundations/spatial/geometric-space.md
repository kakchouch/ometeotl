---
title: "GeometricSpace"
---

Source:
- [src/ometeotl_foundations/spatial/geometric_space.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/geometric_space.py)

Local role:
Frozen generic dataclass that composes a core `Space` with a concrete geometry. The primary user-facing type for spatial spaces in the foundations layer.

Big-picture role:
`GeometricSpace[G]` answers both ontological questions (kind, is_abstract, dimensions) and spatial questions (geometry) through a single object, without touching the `Space` dataclass directly. It is the input type for `derive_space_relations()`.

Design principle: **composition over inheritance** — `GeometricSpace` wraps `Space` rather than subclassing it. This avoids dataclass + Generic[G] inheritance pitfalls and keeps `ometeotl_core` untouched.

## Type parameter

`G` — the concrete geometry type (e.g. `BoundingBox`, or a Shapely wrapper). Must satisfy the `Geometry` protocol.

## Fields

- `space: Space` — the underlying core `Space` object
- `geometry: G` — the geometry describing the spatial extent of the space
- `coordinate_system: CoordinateSystem = CARTESIAN_2D` — coordinate frame of `geometry`
- `metadata: JsonMap = {}` — arbitrary key/value annotations (provenance, confidence, etc.)

Frozen — a geometric space is a value object. Renegotiating a boundary means creating a new `GeometricSpace`.

## Proxy properties (delegate to `space`, no logic duplication)

- `id -> ObjectId` — identifier of the underlying space
- `kind -> str` — kind of the underlying space (e.g. `"physical"`)
- `is_abstract -> bool` — whether the underlying space is non-canonical
- `dimensions -> JsonMap` — dimension map of the underlying space

## Serialisation

- `to_dict() -> JsonMap` — self-contained; calls `geometry.to_dict()` (requires `"type"` discriminator in the result)
- `@classmethod from_dict(data, geometry_deserializer: Callable[[JsonMap], G]) -> GeometricSpace[G]` — injected deserializer pattern; pass `BoundingBox.from_dict` at the foundations layer, or an adapter-specific deserializer otherwise

The injected deserializer makes `from_dict` adapter-agnostic: the caller controls how `G` is reconstructed.

Example:

```python
from ometeotl_core.model.spaces import Space
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.geometric_space import GeometricSpace
from ometeotl_foundations.spatial.coordinate_system import WGS84

space = Space(id="district-1")
space.kind = "physical"
space.set_dimension("population", 50_000)

gs = GeometricSpace(
    space=space,
    geometry=BoundingBox(2.30, 48.80, 2.40, 48.90),
    coordinate_system=WGS84,
    metadata={"source": "cadastral"},
)

assert gs.id == "district-1"
assert gs.kind == "physical"
assert gs.dimensions["population"] == 50_000

# Round-trip
d = gs.to_dict()
restored = GeometricSpace.from_dict(d, BoundingBox.from_dict)
assert restored.geometry == gs.geometry
```

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [BoundingBox](/ometeotl/documentation/class-reference/foundations/spatial/bounding-box/)
- [SpatialExtent](/ometeotl/documentation/class-reference/foundations/spatial/spatial-extent/)
- [derive_space_relations](/ometeotl/documentation/class-reference/foundations/spatial/relation-derivation/)
