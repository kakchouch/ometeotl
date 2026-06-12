---
title: "SpatialIndex Protocol"
---

Source:
- [src/ometeotl_foundations/spatial/spatial_index.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/spatial/spatial_index.py)

Local role:
`runtime_checkable` Protocol for spatially indexed object lookup. Defines the contract that adapter-backed index implementations (e.g. rtree) must satisfy.

Big-picture role:
The foundations layer does not ship a concrete `SpatialIndex` implementation. `SpatialMap` uses a linear O(n) scan that is correct for all inputs. Adapter subclasses of `SpatialMap` override `ids_containing_point` and `ids_intersecting` with a `SpatialIndex`-backed implementation.

## Protocol members

- `insert(object_id: ObjectId, bounds: BoundingBox) -> None` — register `object_id` with its axis-aligned bounding box
- `remove(object_id: ObjectId) -> None` — remove `object_id` from the index; no-op if not present
- `query(bounds: BoundingBox) -> List[ObjectId]` — return IDs of all objects whose bounds intersect `bounds`
- `query_point(point: Coordinate2D) -> List[ObjectId]` — return IDs of all objects whose bounds contain `point`; provided as first-class because point-in-box is the most common lookup and adapters can implement it more efficiently than `query(BoundingBox.from_point(point))`

## Design notes

- No `update()` method — callers use `remove` then `insert` to move an entry.
- All operations are keyed by `ObjectId` (string alias).
- The index stores bounding boxes only, not full geometry objects.

Example (illustrative — no concrete implementation in foundations):

```python
from ometeotl_foundations.spatial.spatial_index import SpatialIndex

# Adapter subclass would implement this protocol:
class MyRtreeIndex:
    def insert(self, object_id, bounds): ...
    def remove(self, object_id): ...
    def query(self, bounds): ...
    def query_point(self, point): ...

from ometeotl_foundations.spatial.spatial_index import SpatialIndex
assert isinstance(MyRtreeIndex(), SpatialIndex)
```

See also:
- [SpatialMap](/ometeotl/documentation/class-reference/foundations/spatial/spatial-map/) — default O(n) implementation
- [SpatialBackend](/ometeotl/documentation/class-reference/foundations/spatial/spatial-backend/) — `make_index()` factory
