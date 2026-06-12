"""Geometry structural Protocol for the spatial foundations layer.

All geometry implementations — BoundingBox (pure Python) and any
adapter-backed wrapper — must satisfy this protocol.

The ``to_dict`` method is part of the contract so that
:class:`~ometeotl_foundations.spatial.geometric_space.GeometricSpace`
can serialise itself without knowing the concrete geometry type.
Every dict produced by ``to_dict`` must include a ``"type"``
discriminator key so deserialisation can dispatch to the right
``from_dict`` implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Protocol, runtime_checkable

from .coordinates import Coordinate2D

if TYPE_CHECKING:
    from .bounding_box import BoundingBox

JsonMap = Dict[str, Any]


@runtime_checkable
class Geometry(Protocol):
    """Contract for all geometry objects in the spatial foundations layer.

    ``runtime_checkable`` allows ``isinstance(obj, Geometry)`` guards in
    :func:`~ometeotl_foundations.spatial.relation_derivation.derive_space_relations`
    and other consumers.

    Implementations must be self-contained value objects; mutation
    (union, buffer) is a construction concern handled by
    :class:`~ometeotl_foundations.spatial.spatial_backend.SpatialBackend`.
    """

    @property
    def area(self) -> float:
        """Area of the geometry in the native units of its coordinate system."""
        ...

    @property
    def centroid(self) -> Coordinate2D:
        """Geometric centroid as a 2-D coordinate."""
        ...

    @property
    def bounds(self) -> "BoundingBox":
        """Axis-aligned bounding box of this geometry."""
        ...

    def contains(self, other: "Geometry") -> bool:
        """Return True if this geometry fully contains *other*."""
        ...

    def intersects(self, other: "Geometry") -> bool:
        """Return True if this geometry shares any interior with *other*."""
        ...

    def touches(self, other: "Geometry") -> bool:
        """Return True if the geometries share a boundary but not interior."""
        ...

    def distance(self, other: "Geometry") -> float:
        """Minimum distance to *other*; 0 if the geometries overlap."""
        ...

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict.

        The returned dict must include a ``"type"`` discriminator key
        (e.g. ``"bounding_box"``, ``"wkt"``) so callers can dispatch to
        the correct ``from_dict`` implementation.
        """
        ...
