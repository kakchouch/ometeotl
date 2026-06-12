---
title: "Foundations / Spatial"
description: "Class reference for ometeotl_foundations/spatial — pure-Python spatial specialization layer"
---

Source:
- [src/ometeotl_foundations/spatial/](https://github.com/kakchouch/ometeotl/tree/main/src/ometeotl_foundations/spatial/)

## Purpose

`ometeotl_foundations/spatial/` is the first-order spatial specialization of `ometeotl_core`. It provides concrete geometry types, coordinate value types, structural protocols, and generic containers — all in pure Python with no library dependency. A Shapely-backed adapter (`ometeotl_adapters/spatial_shapely/`) will implement the same protocols for production use.

## Layer role in the three-tier architecture

```
ometeotl_core          — abstract model (Space, SpaceRelationGraph, …)
ometeotl_foundations   — first-order specialization (this layer)
ometeotl_adapters      — library-backed implementations (Shapely, NetworkX, …)
```

## Public surface

| File | Exports |
|------|---------|
| `coordinates.py` | `Coordinate2D`, `Coordinate3D`, `GeoCoordinate`, `GridCell` |
| `coordinate_system.py` | `CoordinateKind`, `CoordinateSystem`, `CARTESIAN_2D`, `CARTESIAN_3D`, `WGS84`, `GRID` |
| `geometry.py` | `Geometry` (Protocol) |
| `bounding_box.py` | `BoundingBox` |
| `spatial_index.py` | `SpatialIndex` (Protocol) |
| `spatial_backend.py` | `SpatialBackend` (Protocol) |
| `geometric_space.py` | `GeometricSpace[G]` |
| `spatial_extent.py` | `SpatialExtent[G]` |
| `spatial_map.py` | `SpatialMap[G]` |
| `relation_derivation.py` | `derive_space_relations()` |

## Pages in this section

- [Coordinate2D / Coordinate3D / GeoCoordinate / GridCell](/ometeotl/documentation/class-reference/foundations/spatial/coordinates/)
- [CoordinateKind / CoordinateSystem / predefined singletons](/ometeotl/documentation/class-reference/foundations/spatial/coordinate-system/)
- [Geometry Protocol](/ometeotl/documentation/class-reference/foundations/spatial/geometry/)
- [BoundingBox](/ometeotl/documentation/class-reference/foundations/spatial/bounding-box/)
- [SpatialIndex Protocol](/ometeotl/documentation/class-reference/foundations/spatial/spatial-index/)
- [SpatialBackend Protocol](/ometeotl/documentation/class-reference/foundations/spatial/spatial-backend/)
- [GeometricSpace](/ometeotl/documentation/class-reference/foundations/spatial/geometric-space/)
- [SpatialExtent](/ometeotl/documentation/class-reference/foundations/spatial/spatial-extent/)
- [SpatialMap](/ometeotl/documentation/class-reference/foundations/spatial/spatial-map/)
- [derive_space_relations](/ometeotl/documentation/class-reference/foundations/spatial/relation-derivation/)
