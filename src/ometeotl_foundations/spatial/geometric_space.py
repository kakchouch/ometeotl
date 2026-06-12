"""GeometricSpace: ready-to-use composition of a core Space and a geometry.

GeometricSpace[G] wraps an ``ometeotl_core`` Space together with a
geometry value, giving callers a single object that answers both
ontological questions (kind, is_abstract, dimensions) and spatial
questions (contains, intersects, distance) without touching the Space
dataclass directly.

Design notes:
- Composition over inheritance: GeometricSpace wraps Space rather than
  subclassing it.  This avoids dataclass + Generic[G] inheritance
  pitfalls and keeps the IO layer of ometeotl_core untouched.
- Frozen: geometry extents are value objects.  Renegotiating a boundary
  means creating a new GeometricSpace, not mutating an existing one.
- Serialisation: ``to_dict`` is self-contained (delegates to
  ``geometry.to_dict()``).  ``from_dict`` requires an injected
  ``geometry_deserializer`` callable because deserialising G is
  adapter-specific (e.g. ``BoundingBox.from_dict`` for the foundations
  layer, a shapely wrapper deserialiser for the adapter layer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Mapping, TypeVar

from ometeotl_core.model.base import JsonMap, ObjectId, _canonical_json_map
from ometeotl_core.model.spaces import Space

from .coordinate_system import CARTESIAN_2D, CoordinateSystem
from .geometry import Geometry

G = TypeVar("G")


@dataclass(frozen=True)
class GeometricSpace(Generic[G]):
    """A core Space paired with a concrete geometry.

    Attributes:
        space: The underlying ometeotl_core Space object.
        geometry: The geometry describing the spatial extent of the space.
            Must satisfy the
            :class:`~ometeotl_foundations.spatial.geometry.Geometry`
            protocol.
        coordinate_system: The coordinate frame of *geometry*.  Defaults
            to :data:`~ometeotl_foundations.spatial.coordinate_system.CARTESIAN_2D`.
        metadata: Arbitrary key/value annotations (provenance, confidence,
            etc.).  Follows the same ``JsonMap`` convention as core model
            objects.

    Proxied properties (read-only, delegate to ``space``):
        id, kind, is_abstract, dimensions
    """

    space: Space
    geometry: G
    coordinate_system: CoordinateSystem = field(default=CARTESIAN_2D)
    metadata: JsonMap = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Proxy properties — no logic duplication, pure delegation
    # ------------------------------------------------------------------

    @property
    def id(self) -> ObjectId:
        """Identifier of the underlying space."""
        return self.space.id

    @property
    def kind(self) -> str:
        """Kind of the underlying space (e.g. ``"physical"``)."""
        return self.space.kind

    @property
    def is_abstract(self) -> bool:
        """Whether the underlying space is abstract (non-canonical)."""
        return self.space.is_abstract

    @property
    def dimensions(self) -> JsonMap:
        """Dimension map of the underlying space."""
        return self.space.dimensions

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict.

        The ``geometry`` entry is produced by ``self.geometry.to_dict()``,
        which must include a ``"type"`` discriminator key so that
        ``from_dict`` can dispatch to the correct deserialiser.
        """
        geom_serialisable: Any = self.geometry
        return {
            "space": self.space.to_dict(),
            "geometry": geom_serialisable.to_dict(),
            "coordinate_system": self.coordinate_system.to_dict(),
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        geometry_deserializer: Callable[[JsonMap], G],
    ) -> "GeometricSpace[G]":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Args:
            data: The serialised representation.
            geometry_deserializer: A callable that reconstructs the
                geometry from its ``JsonMap`` representation.  Pass
                ``BoundingBox.from_dict`` when working at the foundations
                layer, or an adapter-specific deserialiser otherwise.

        Raises:
            ValueError: If required keys are absent or the space / CRS
                cannot be reconstructed.
            KeyError: If expected keys are missing from *data*.
        """
        raw_metadata = data.get("metadata") or {}
        return cls(
            space=Space.from_dict(data["space"]),
            geometry=geometry_deserializer(data["geometry"]),
            coordinate_system=CoordinateSystem.from_dict(data["coordinate_system"]),
            metadata=dict(raw_metadata),
        )
