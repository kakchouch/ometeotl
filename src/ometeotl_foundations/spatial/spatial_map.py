"""SpatialMap: mutable container mapping ObjectId → SpatialExtent[G].

SpatialMap is a concrete mutable container, not a Protocol.  The
default implementation uses a linear O(n) scan for spatial queries.
Adapter subclasses can override ``ids_containing_point`` and
``ids_intersecting`` with a SpatialIndex-backed implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Generic, List, Optional, TypeVar

from ometeotl_core.model.base import ObjectId

from .bounding_box import BoundingBox
from .coordinates import Coordinate2D
from .geometry import Geometry
from .spatial_extent import SpatialExtent

G = TypeVar("G", bound=Geometry)


@dataclass
class SpatialMap(Generic[G]):
    """Mutable mapping from ObjectId to SpatialExtent[G].

    Suitable for both space extents (space_id → SpatialExtent describing
    the space's geometry) and object positions (actor_id → SpatialExtent
    describing the actor's footprint).

    The two query helpers (``ids_containing_point`` and
    ``ids_intersecting``) perform a linear scan over all registered
    extents.  They are correct for any G that satisfies the Geometry
    protocol, but O(n) in the number of registered objects.  Adapter
    subclasses should override these with an index-backed implementation
    when performance matters.
    """

    _extents: Dict[ObjectId, SpatialExtent[G]] = field(
        default_factory=dict, init=False, repr=False
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def set_extent(self, object_id: ObjectId, extent: SpatialExtent[G]) -> None:
        """Register or replace the spatial extent for *object_id*."""
        self._extents[object_id] = extent

    def remove_extent(self, object_id: ObjectId) -> None:
        """Remove *object_id* from the map.

        No-op if *object_id* is not present.
        """
        self._extents.pop(object_id, None)

    def get_extent(self, object_id: ObjectId) -> Optional[SpatialExtent[G]]:
        """Return the extent for *object_id*, or None if not registered."""
        return self._extents.get(object_id)

    def all_ids(self) -> List[ObjectId]:
        """Return all registered object IDs in sorted order."""
        return sorted(self._extents.keys())

    def as_dict(self) -> Dict[ObjectId, SpatialExtent[G]]:
        """Return a shallow copy of the internal mapping."""
        return dict(self._extents)

    # ------------------------------------------------------------------
    # Spatial queries — O(n) linear scan
    # ------------------------------------------------------------------

    def ids_containing_point(self, point: Coordinate2D) -> List[ObjectId]:
        """Return IDs of all objects whose geometry contains *point*.

        Uses ``geometry.contains(BoundingBox.from_point(point))`` for
        each registered extent.  Returns results in sorted order.
        """
        point_box = BoundingBox.from_point(point)
        return sorted(
            oid
            for oid, extent in self._extents.items()
            if extent.geometry.contains(point_box)  # type: ignore[attr-defined]
        )

    def ids_intersecting(self, bounds: BoundingBox) -> List[ObjectId]:
        """Return IDs of all objects whose geometry intersects *bounds*.

        Uses ``geometry.intersects(bounds)`` for each registered extent.
        Returns results in sorted order.
        """
        return sorted(
            oid
            for oid, extent in self._extents.items()
            if extent.geometry.intersects(bounds)  # type: ignore[attr-defined]
        )
