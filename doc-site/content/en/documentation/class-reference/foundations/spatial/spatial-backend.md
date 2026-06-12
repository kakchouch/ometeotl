---
title: "SpatialBackend Protocol"
---

Source:
- [src/ometeotl_foundations/spatial/spatial_backend.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/spatial_backend.py)

Local role:
`runtime_checkable` Protocol defining the adapter factory interface. An adapter backend implements this protocol to expose library-backed geometry construction and spatial indexing to the rest of the system.

Big-picture role:
The foundations layer itself does not provide a concrete backend — `BoundingBox` is the pure-Python fallback geometry. The Shapely adapter (`ometeotl_adapters/spatial_shapely/`) will implement this protocol using `shapely.geometry.*` factories.

## Protocol members

- `make_point(coord: Coordinate2D) -> Geometry` — create a point geometry from a 2-D coordinate
- `make_point_3d(coord: Coordinate3D) -> Geometry` — create a point geometry from a 3-D coordinate
- `make_polygon(exterior: List[Coordinate2D]) -> Geometry` — create a simple polygon from an exterior ring; backends close the ring internally if needed
- `make_buffer(geom: Geometry, distance: float) -> Geometry` — return `geom` expanded by `distance` (in native units of the geometry's coordinate system)
- `make_bounding_box(min_x, min_y, max_x, max_y) -> Geometry` — create a rectangular geometry from explicit AABB coordinates; may return a `BoundingBox` or a library-specific rectangle
- `make_index() -> SpatialIndex` — create an empty spatial index backed by this adapter

## Design notes

- Typed coordinate arguments (`Coordinate2D`, `Coordinate3D`) rather than variadic `*coords` prevent arity bugs and preserve type-checker information.
- Construction operations (buffer, union) are on `SpatialBackend`, not on the `Geometry` protocol — geometry objects are value objects; the backend is the factory.

Example (illustrative — implementation lives in the adapter layer):

```python
from ometeotl_foundations.spatial.spatial_backend import SpatialBackend
from ometeotl_foundations.spatial.coordinates import Coordinate2D

# Adapter would be injected by the caller
def build_zone(backend: SpatialBackend, corners):
    poly = backend.make_polygon(corners)
    buffered = backend.make_buffer(poly, distance=10.0)
    return buffered
```

See also:
- [Geometry Protocol](/ometeotl/documentation/class-reference/foundations/spatial/geometry/)
- [SpatialIndex Protocol](/ometeotl/documentation/class-reference/foundations/spatial/spatial-index/)
