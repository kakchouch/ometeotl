---
title: "Coordinate2D / Coordinate3D / GeoCoordinate / GridCell"
---

Source:
- [src/ometeotl_foundations/spatial/coordinates.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/coordinates.py)

Local role:
Pure immutable value types for expressing positions. No geometry logic — arithmetic, distance, and projection belong to `Geometry` implementations.

## Coordinate2D

Frozen dataclass. A position in a flat 2-D Cartesian or projected plane.

Fields:
- `x: float`
- `y: float`

## Coordinate3D

Frozen dataclass. A position in a 3-D Cartesian space.

Fields:
- `x: float`
- `y: float`
- `z: float`

## GeoCoordinate

Frozen dataclass. A geographic position in the GeoJSON longitude/latitude convention.

Fields:
- `longitude: float` — validated to `[-180, 180]`
- `latitude: float` — validated to `[-90, 90]`
- `altitude: float = 0.0`

Raises `ValueError` on construction if either range is violated.

## GridCell

Frozen dataclass. A discrete position in a tile or hex grid.

Fields:
- `col: int`
- `row: int`
- `layer: int = 0` — defaults to 0 for 2-D grids; negative values are valid

Example:

```python
from ometeotl_foundations.spatial.coordinates import (
    Coordinate2D, Coordinate3D, GeoCoordinate, GridCell
)

pt = Coordinate2D(x=3.5, y=7.0)
geo = GeoCoordinate(longitude=2.35, latitude=48.85)  # Paris
cell = GridCell(col=4, row=2)
```

See also:
- [BoundingBox](/ometeotl/documentation/class-reference/foundations/spatial/bounding-box/) — uses `Coordinate2D` for `centroid` and `from_point`
- [CoordinateSystem](/ometeotl/documentation/class-reference/foundations/spatial/coordinate-system/) — describes the frame in which coordinates are interpreted
