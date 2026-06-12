"""SpatialIndex Protocol for efficient spatial lookup.

Adapter implementations (e.g. rtree-backed) implement this protocol.
The foundations layer does not provide a concrete implementation;
:class:`~ometeotl_foundations.spatial.spatial_map.SpatialMap` uses a
linear scan that is correct for any number of objects but O(n).
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from ometeotl_core.model.base import ObjectId

from .bounding_box import BoundingBox
from .coordinates import Coordinate2D


@runtime_checkable
class SpatialIndex(Protocol):
    """Protocol for spatially indexed object lookup.

    All operations are keyed by ``ObjectId`` (string).  The index stores
    axis-aligned bounding boxes; callers insert the bounding box of each
    object and query by a bounding box or point.

    No ``update`` method is provided by design: callers call
    :meth:`remove` then :meth:`insert` to move an entry.
    """

    def insert(self, object_id: ObjectId, bounds: BoundingBox) -> None:
        """Register *object_id* with its axis-aligned *bounds*."""
        ...

    def remove(self, object_id: ObjectId) -> None:
        """Remove *object_id* from the index.

        No-op if *object_id* is not present.
        """
        ...

    def query(self, bounds: BoundingBox) -> List[ObjectId]:
        """Return IDs of all objects whose bounds intersect *bounds*."""
        ...

    def query_point(self, point: Coordinate2D) -> List[ObjectId]:
        """Return IDs of all objects whose bounds contain *point*.

        Provided as a first-class method because point-in-box is the most
        common spatial lookup and adapters can implement it more
        efficiently than ``query(BoundingBox.from_point(point))``.
        """
        ...
