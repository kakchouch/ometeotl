"""SpatialExtent: geometric position of an object within a reference space.

SpatialExtent[G] records where a non-space object (actor, resource, etc.)
is located within a named coordinate frame.  It is intentionally distinct
from GeometricSpace[G]:

- GeometricSpace describes what shape a *space* IS.
- SpatialExtent describes where an *object* IS within a space.

The ``space_id`` is a loose reference (by ObjectId string) to the
GeometricSpace that defines the coordinate frame.  This keeps SpatialExtent
lightweight and avoids a hard dependency on the GeometricSpace collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Mapping, TypeVar

from ometeotl_core.model.base import JsonMap, ObjectId, _canonical_json_map

from .coordinate_system import CARTESIAN_2D, CoordinateSystem

G = TypeVar("G")


@dataclass(frozen=True)
class SpatialExtent(Generic[G]):
    """Geometric footprint or position of an object within a reference space.

    Attributes:
        space_id: Identifier of the coordinate-frame space (a loose
            reference to a GeometricSpace by ID).
        geometry: The object's footprint / position geometry.  Must
            satisfy the
            :class:`~ometeotl_foundations.spatial.geometry.Geometry`
            protocol.
        coordinate_system: The coordinate frame of *geometry*.  Defaults
            to :data:`~ometeotl_foundations.spatial.coordinate_system.CARTESIAN_2D`.
        metadata: Arbitrary key/value annotations.
    """

    space_id: ObjectId
    geometry: G
    coordinate_system: CoordinateSystem = field(default=CARTESIAN_2D)
    metadata: JsonMap = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict.

        The ``geometry`` entry is produced by ``self.geometry.to_dict()``.
        """
        geom_serialisable: Any = self.geometry
        return {
            "space_id": self.space_id,
            "geometry": geom_serialisable.to_dict(),
            "coordinate_system": self.coordinate_system.to_dict(),
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        geometry_deserializer: Callable[[JsonMap], G],
    ) -> "SpatialExtent[G]":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Args:
            data: The serialised representation.
            geometry_deserializer: Callable that reconstructs G from its
                ``JsonMap`` representation (e.g. ``BoundingBox.from_dict``).

        Raises:
            ValueError: If required keys are absent.
            KeyError: If expected keys are missing from *data*.
        """
        raw_metadata = data.get("metadata") or {}
        return cls(
            space_id=str(data["space_id"]),
            geometry=geometry_deserializer(data["geometry"]),
            coordinate_system=CoordinateSystem.from_dict(data["coordinate_system"]),
            metadata=dict(raw_metadata),
        )
