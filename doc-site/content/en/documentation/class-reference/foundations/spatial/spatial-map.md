---
title: "SpatialMap"
---

Source:
- [src/ometeotl_foundations/spatial/spatial_map.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/spatial_map.py)

Local role:
Mutable generic container mapping `ObjectId → SpatialExtent[G]`. Concrete class — not a Protocol.

Big-picture role:
Tracks spatial positions for actors, resources, or any other objects within a coordinate frame. The default implementation scans all extents linearly for spatial queries; adapter subclasses override the query methods with a `SpatialIndex`-backed implementation for O(log n) performance.

## Type parameter

`G` — bound to `Geometry`. The concrete geometry type stored in all extents within this map.

## Fields

- `_extents: Dict[ObjectId, SpatialExtent[G]]` — internal store; not exposed directly (use accessor methods)

## CRUD methods

- `set_extent(object_id, extent: SpatialExtent[G]) -> None` — register or replace the spatial extent for `object_id`
- `remove_extent(object_id) -> None` — remove `object_id`; no-op if not present
- `get_extent(object_id) -> Optional[SpatialExtent[G]]` — return the extent or `None`
- `all_ids() -> List[ObjectId]` — sorted list of all registered IDs
- `as_dict() -> Dict[ObjectId, SpatialExtent[G]]` — shallow copy of the internal mapping

## Spatial queries (O(n) linear scan)

- `ids_containing_point(point: Coordinate2D) -> List[ObjectId]` — sorted IDs of all objects whose geometry contains `point`; uses `geometry.contains(BoundingBox.from_point(point))`
- `ids_intersecting(bounds: BoundingBox) -> List[ObjectId]` — sorted IDs of all objects whose geometry intersects `bounds`

Both return results in sorted order and are correct for any `G` satisfying the `Geometry` protocol.

## Adapter subclassing

Override `ids_containing_point` and `ids_intersecting` to use a `SpatialIndex` (e.g. rtree). Pass a `SpatialIndex` instance created via `SpatialBackend.make_index()`.

Example:

```python
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinates import Coordinate2D
from ometeotl_foundations.spatial.spatial_extent import SpatialExtent
from ometeotl_foundations.spatial.spatial_map import SpatialMap

smap: SpatialMap[BoundingBox] = SpatialMap()

smap.set_extent("actor-1", SpatialExtent(space_id="zone", geometry=BoundingBox(0, 0, 5, 5)))
smap.set_extent("actor-2", SpatialExtent(space_id="zone", geometry=BoundingBox(3, 3, 8, 8)))

# Which actors contain point (4, 4)?
print(smap.ids_containing_point(Coordinate2D(4, 4)))  # ['actor-1', 'actor-2']

# Which actors intersect a query box?
print(smap.ids_intersecting(BoundingBox(7, 7, 10, 10)))  # ['actor-2']
```

See also:
- [SpatialExtent](/ometeotl/documentation/class-reference/foundations/spatial/spatial-extent/)
- [SpatialIndex Protocol](/ometeotl/documentation/class-reference/foundations/spatial/spatial-index/)
- [BoundingBox](/ometeotl/documentation/class-reference/foundations/spatial/bounding-box/)
