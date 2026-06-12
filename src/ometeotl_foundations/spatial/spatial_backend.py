"""SpatialBackend Protocol: adapter factory interface.

An adapter (e.g. ``ometeotl_adapters.spatial_shapely``) implements this
protocol to provide library-backed geometry construction and spatial
indexing.  The foundations layer itself does not provide a concrete
backend; ``BoundingBox`` is the pure-Python fallback geometry.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from .bounding_box import BoundingBox
from .coordinates import Coordinate2D, Coordinate3D
from .geometry import Geometry
from .spatial_index import SpatialIndex


@runtime_checkable
class SpatialBackend(Protocol):
    """Factory interface that adapter backends must satisfy.

    All factory methods return objects implementing the
    :class:`~ometeotl_foundations.spatial.geometry.Geometry` protocol.
    Typed coordinate arguments are used instead of variadic ``*coords``
    to prevent arity bugs and preserve type-checker information.
    """

    def make_point(self, coord: Coordinate2D) -> Geometry:
        """Create a point geometry from a 2-D coordinate."""
        ...

    def make_point_3d(self, coord: Coordinate3D) -> Geometry:
        """Create a point geometry from a 3-D coordinate."""
        ...

    def make_polygon(self, exterior: List[Coordinate2D]) -> Geometry:
        """Create a simple polygon from an exterior ring of 2-D coordinates.

        The ring need not be explicitly closed (first == last); backends
        should close it internally if required.
        """
        ...

    def make_buffer(self, geom: Geometry, distance: float) -> Geometry:
        """Return a new geometry that is *geom* expanded by *distance*.

        *distance* is in the native units of the geometry's coordinate
        system.
        """
        ...

    def make_bounding_box(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> Geometry:
        """Create a rectangular geometry from explicit AABB coordinates.

        Backends may return a :class:`BoundingBox` directly or a
        library-specific rectangle geometry.
        """
        ...

    def make_index(self) -> SpatialIndex:
        """Create an empty spatial index backed by this adapter."""
        ...
