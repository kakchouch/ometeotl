---
title: "CoordinateKind / CoordinateSystem / Predefined Singletons"
---

Source:
- [src/ometeotl_foundations/spatial/coordinate_system.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/coordinate_system.py)

Local role:
Vocabulary for describing coordinate frames attached to geometries and spatial extents.

## CoordinateKind

`str, Enum`. Nature of a coordinate system. Inherits from `str` so values serialise to their string form without a custom JSON encoder.

Values:
- `CARTESIAN = "cartesian"`
- `GEOGRAPHIC = "geographic"`
- `GRID = "grid"`
- `CUSTOM = "custom"`

## CoordinateSystem

Frozen dataclass. Describes the coordinate frame used by a geometry or extent.

Fields:
- `name: str` — human-readable identifier (e.g. `"wgs84"`)
- `kind: CoordinateKind` — broad category
- `unit: str` — native unit of measure (`"meter"`, `"degree"`, `"cell"`)
- `srid: Optional[int] = None` — EPSG code for geographic/projected systems

Methods:
- `to_dict() -> JsonMap` — serialise to a plain dict; `srid` is omitted when `None`
- `@classmethod from_dict(data) -> CoordinateSystem` — reconstruct from dict; raises `ValueError` on missing or invalid `kind`

## Predefined singletons

| Name | kind | unit | srid |
|------|------|------|------|
| `CARTESIAN_2D` | `cartesian` | `meter` | — |
| `CARTESIAN_3D` | `cartesian` | `meter` | — |
| `WGS84` | `geographic` | `degree` | 4326 |
| `GRID` | `grid` | `cell` | — |

Example:

```python
from ometeotl_foundations.spatial.coordinate_system import (
    CoordinateSystem, CoordinateKind, CARTESIAN_2D, WGS84
)

# Use a predefined singleton
cs = CARTESIAN_2D

# Reconstruct from dict (e.g. after JSON deserialisation)
cs2 = CoordinateSystem.from_dict(cs.to_dict())
assert cs2 == cs

# Custom CRS
custom = CoordinateSystem(
    name="local_grid",
    kind=CoordinateKind.CUSTOM,
    unit="meter",
)
```

See also:
- [GeometricSpace](/ometeotl/documentation/class-reference/foundations/spatial/geometric-space/)
- [SpatialExtent](/ometeotl/documentation/class-reference/foundations/spatial/spatial-extent/)
